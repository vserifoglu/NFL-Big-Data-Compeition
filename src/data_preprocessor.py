import pandas as pd
import numpy as np
import gc
from typing import Generator, Tuple, List
from src.schema import PreprocessedSchema

class DataPreProcessor:
    def __init__(self):
        self.output_schema = PreprocessedSchema
        self.keep_cols = list(self.output_schema.to_schema().columns.keys())

    def filter_context(self, supp_df):
        """
        Filters the supplementary dataframe and performs 'Lightweight Feature Engineering'..
        """

        # Calculate Possession Win Probability
        supp_df['possession_win_prob'] = np.where(
            supp_df['possession_team'] == supp_df['home_team_abbr'],
            supp_df['pre_snap_home_team_win_probability'],
            supp_df['pre_snap_visitor_team_win_probability'],
        )
        
        # Calculate Normalized Field Position (0-100 Scale)
        # Logic: If on own side, use number. If on opp side, use 100 - number.
        supp_df['yards_from_own_goal'] = np.where(
            supp_df['yardline_side'] == supp_df['possession_team'],
            supp_df['yardline_number'],           
            100 - supp_df['yardline_number']      
        )

        # valid mask filters
        valid_mask = (
            (supp_df['team_coverage_man_zone'].astype(str).str.contains('Zone', case=False, na=False)) &
            (supp_df['pass_result'].isin(['C', 'I', 'IN'])) &
            (supp_df['team_coverage_type'] != 'COVER_6_ZONE') &
            (~supp_df['dropback_type'].str.upper().isin([
                'SCRAMBLE', 'SCRAMBLE_ROLLOUT_LEFT', 'SCRAMBLE_ROLLOUT_RIGHT', 'QB_DRAW'])) &
            (supp_df['play_nullified_by_penalty'] != 'Y')
        )

        # remove trick / cheap plays
        screen_shovel_mask = (
            supp_df['route_of_targeted_receiver'].astype(str).str.upper().str.contains('SCREEN', na=False) | 
            
            # Physics Check: Ball caught behind or at LOS (Shovels/Swings)
            (supp_df['pass_length'] <= 0) | 
            
            # Check-downs (Flat routes < 3 yards)
            (
                (supp_df['route_of_targeted_receiver'].astype(str).str.upper() == 'FLAT') & 
                (supp_df['pass_length'] < 3)
            )
        )
        
        # base situations
        base_situation_mask = (           
            (supp_df['down'].isin([1, 2])) &
            
            # Competitive Game (Neutral Script)
            (supp_df['possession_win_prob'].between(0.20, 0.80)) & 

            # On Schedule (Not 1st & 20 or 2nd & 18)
            (supp_df['yards_to_go'] <= 10) &
            
            # We use our new engineered column here
            (supp_df['yards_from_own_goal'].between(20, 80))
        )
        
        final_valid_mask = (
            valid_mask &
            (~screen_shovel_mask) &
            base_situation_mask
        )

        return supp_df[final_valid_mask].copy()

    def _stitch_tracking_data(self, input_df, output_df, valid_keys):
        """
        Pure Logic. Merges Pre-Throw and Post-Throw data.
        """
        # Filter Input
        input_df['key_tuple'] = list(zip(input_df.game_id, input_df.play_id))
        input_df = input_df[input_df['key_tuple'].isin(valid_keys)].drop(columns=['key_tuple'])
        input_df['phase'] = 'pre_throw'
        
        if output_df.empty: return input_df

        # Filter Output
        output_df['key_tuple'] = list(zip(output_df.game_id, output_df.play_id))
        output_df = output_df[output_df['key_tuple'].isin(valid_keys)].drop(columns=['key_tuple'])
        
        # Logic: Tag first frame of Output as pass_forward
        output_df['event'] = None
        output_df.loc[output_df['frame_id'] == 1, 'event'] = 'pass_forward'
        
        # TODO: move this to schema
        # Metadata Propagation (Players missing in Output get this from Input)
        meta_cols = ['game_id', 'play_id', 'nfl_id', 'player_name', 'jersey_number', 'player_position', 
                     'player_role', 'player_side', 'play_direction', 'absolute_yardline_number', 
                     'ball_land_x', 'ball_land_y']
        
        avail_cols = [c for c in meta_cols if c in input_df.columns]
        player_meta = input_df[avail_cols].drop_duplicates(subset=['game_id', 'play_id', 'nfl_id'])
        
        # Frame Offset Calculation
        play_offsets = input_df.groupby(['game_id', 'play_id'])['frame_id'].max().reset_index()
        play_offsets.columns = ['game_id', 'play_id', 'offset']
        
        output_df = output_df.merge(player_meta, on=['game_id', 'play_id', 'nfl_id'], how='left')
        output_df = output_df.merge(play_offsets, on=['game_id', 'play_id'], how='left')
        
        # Apply Offset
        output_df['frame_id'] = output_df['frame_id'] + output_df['offset'].fillna(0)
        output_df['phase'] = 'post_throw'
        
        df = pd.concat([input_df, output_df.drop(columns=['offset'])], ignore_index=True)

        return df

    def _normalize_coordinates(self, df):
        """
        Standardizes field geometry to Left->Right drive direction.
        """
        if 'play_direction' not in df.columns: return df
        mask = df['play_direction'].str.lower() == 'left'
        
        for col in ['x', 'ball_land_x']:
            if col in df.columns: df.loc[mask, col] = 120 - df.loc[mask, col]

        for col in ['y', 'ball_land_y']:
            if col in df.columns: df.loc[mask, col] = 53.3 - df.loc[mask, col]

        return df

    def _clean_and_deduplicate(self, df):
        """
        Ensures strict temporal ordering and removes duplicate frames at the stitch point.
        """
        df['phase_rank'] = df['phase'].apply(lambda x: 1 if x == 'pre_throw' else 2)        
        
        df = df.sort_values(['game_id', 'play_id', 'nfl_id', 'frame_id', 'phase_rank'])        
        
        df = df.drop_duplicates(subset=['game_id', 'play_id', 'nfl_id', 'frame_id'], keep='last')
        
        return df.drop(columns=['phase_rank'])

    def process_single_week(self, week_num, input_df, output_df, context_df):
        """
        Internal logic for a single week.
        """
        valid_keys = set(zip(context_df.game_id, context_df.play_id))

        week_df = self._stitch_tracking_data(input_df, output_df, valid_keys)

        week_df = week_df.merge(context_df, on=['game_id', 'play_id'], how='inner')

        week_df = self._normalize_coordinates(week_df)

        week_df['los_x'] = week_df['ball_land_x'] - week_df['pass_length']
        week_df['week'] = int(week_num)

        week_df = self._clean_and_deduplicate(week_df)

        return self.output_schema.validate(week_df)

    def run(self, data_stream: Generator[Tuple[str, pd.DataFrame, pd.DataFrame], None, None], 
            raw_context_df: pd.DataFrame) -> pd.DataFrame:
        """
        MAIN ENTRY POINT.
        """
        clean_context = self.filter_context(raw_context_df)
        
        processed_chunks: List[pd.DataFrame] = []
        for week_num, input_df, output_df in data_stream:
            
            clean_week_df = self.process_single_week(week_num, input_df, output_df, clean_context)

            if not clean_week_df.empty:
                processed_chunks.append(clean_week_df)

            del input_df, output_df
            gc.collect()

        if not processed_chunks:
            return pd.DataFrame()
        
        return pd.concat(processed_chunks, ignore_index=True)