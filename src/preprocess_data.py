import os
import glob
import pandas as pd
import numpy as np
import re
import gc
import logging


class ZoneCoverageETL:
    def __init__(self, input_dir='data/train', supp_file='data/supplementary_data.csv', output_file='data/processed/master_zone_tracking.csv'):
        """Initializes ETL pipeline configuration and file paths."""
        self.input_dir = input_dir
        self.supp_file = supp_file
        self.output_file = output_file
        self.keep_cols = [
            'game_id', 'play_id', 'nfl_id', 'frame_id', 'phase',
            'x', 'y', 's', 'a', 'dir', 'o',
            'player_name', 'player_position', 'player_role', 'player_side',
            'team_coverage_man_zone', 'pass_result', 'expected_points_added',
            'ball_land_x', 'ball_land_y', 'play_direction'
        ]

    @staticmethod
    def standardize_columns(df):
        """Standardizes column names and enforces ID types."""
        rename_map = {
            'gameId': 'game_id', 'playId': 'play_id', 'nflId': 'nfl_id',
            'frameId': 'frame_id', 'displayName': 'player_name',
            'playDirection': 'play_direction', 'position': 'player_position',
            'x': 'x', 'y': 'y', 's': 's', 'a': 'a', 'dir': 'dir', 'o': 'o'
        }
        df = df.rename(columns=rename_map)
        if 'nfl_id' in df.columns:
            df['nfl_id'] = pd.to_numeric(df['nfl_id'], errors='coerce').fillna(-1).astype(int)
        return df

    @staticmethod
    def normalize_tracking_data(df):
        """Normalizes field coordinates so offense always moves left-to-right."""
        if 'play_direction' not in df.columns:
            return df
        mask = df['play_direction'].str.lower() == 'left'
        df.loc[mask, 'x'] = 120 - df.loc[mask, 'x']
        df.loc[mask, 'y'] = 53.3 - df.loc[mask, 'y']
        if 'dir' in df.columns:
            df.loc[mask, 'dir'] = (df.loc[mask, 'dir'] + 180) % 360
        if 'o' in df.columns:
            df.loc[mask, 'o'] = (df.loc[mask, 'o'] + 180) % 360
        if 'ball_land_x' in df.columns:
            df.loc[mask, 'ball_land_x'] = 120 - df.loc[mask, 'ball_land_x']
        if 'ball_land_y' in df.columns:
            df.loc[mask, 'ball_land_y'] = 53.3 - df.loc[mask, 'ball_land_y']
        return df

    def get_valid_plays_lookup(self):
        """Loads supplementary data and returns valid play keys and context for zone coverage plays."""
        try:
            supp_df = pd.read_csv(self.supp_file, low_memory=False)
            supp_df = self.standardize_columns(supp_df)
            valid_mask = (
                (supp_df['team_coverage_man_zone'].astype(str).str.contains('Zone', case=False, na=False)) &
                (supp_df['pass_result'].isin(['C', 'I', 'IN']))
            )
            valid_df = supp_df[valid_mask].copy()
            valid_keys = set(zip(valid_df.game_id, valid_df.play_id))
            context_cols = ['game_id', 'play_id', 'team_coverage_man_zone', 'pass_result', 'expected_points_added']
            return valid_df[context_cols], valid_keys
        except FileNotFoundError:
            raise FileNotFoundError(f"Critical Error: {self.supp_file} not found.")

    def process_week_data(self, week_num, input_path, output_path, valid_keys, context_df):
        """Processes and merges pre- and post-throw tracking data for a single week, with validation for frame gaps and missing metadata."""
        input_df = pd.read_csv(input_path, low_memory=False)
        input_df = self.standardize_columns(input_df)
        input_df['key_tuple'] = list(zip(input_df.game_id, input_df.play_id))
        input_df = input_df[input_df['key_tuple'].isin(valid_keys)].drop(columns=['key_tuple'])
        if input_df.empty:
            logging.warning(f"No valid input data for week {week_num}.")
            return pd.DataFrame()

        # Load Output
        if output_path and os.path.exists(output_path):
            output_df = pd.read_csv(output_path, low_memory=False)
            output_df = self.standardize_columns(output_df)
            output_df['key_tuple'] = list(zip(output_df.game_id, output_df.play_id))
            output_df = output_df[output_df['key_tuple'].isin(valid_keys)].drop(columns=['key_tuple'])
        else:
            output_df = pd.DataFrame()

        meta_cols = ['game_id', 'play_id', 'nfl_id', 'player_name', 'player_position', 'player_role', 'player_side', 'play_direction', 'ball_land_x', 'ball_land_y']
        avail_meta_cols = [c for c in meta_cols if c in input_df.columns]
        player_meta = input_df[avail_meta_cols].drop_duplicates(subset=['game_id', 'play_id', 'nfl_id'])

        # Track gap and metadata issues for each play
        play_gap_info = {}
        
        # Stitching Logic with Frame Alignment Check
        if not output_df.empty:
            play_offsets = input_df.groupby(['game_id', 'play_id'])['frame_id'].max().reset_index()
            play_offsets.columns = ['game_id', 'play_id', 'offset']
            output_df = output_df.merge(player_meta, on=['game_id', 'play_id', 'nfl_id'], how='left')
            output_df = output_df.merge(play_offsets, on=['game_id', 'play_id'], how='left')

            # Frame alignment check for each play
            for (gid, pid), group in input_df.groupby(['game_id', 'play_id']):
                pre_max = group['frame_id'].max()
                post_group = output_df[(output_df['game_id'] == gid) & (output_df['play_id'] == pid)]
                has_gap = False
                if not post_group.empty:
                    post_min = post_group['frame_id'].min()
                    if post_min != pre_max + 1:
                        has_gap = True

                play_gap_info[(gid, pid)] = has_gap

            output_df['frame_id'] = output_df['frame_id'] + output_df['offset'].fillna(0)
            output_df = output_df.drop(columns=['offset'])
            input_df['phase'] = 'pre_throw'
            output_df['phase'] = 'post_throw'
            full_week = pd.concat([input_df, output_df], ignore_index=True)
        else:
            input_df['phase'] = 'pre_throw'
            for (gid, pid), group in input_df.groupby(['game_id', 'play_id']):
                play_gap_info[(gid, pid)] = False
            full_week = input_df

        full_week = self.normalize_tracking_data(full_week)
        full_week = full_week.merge(context_df, on=['game_id', 'play_id'], how='left')
        
        # --- SELF-HEALING LOGIC: Calculate s, dir, o from coordinates ---
        # Sort by play and frame to ensure correct diff calculation
        full_week = full_week.sort_values(['game_id', 'play_id', 'nfl_id', 'frame_id'])
        
        # Calculate deltas
        # Group by player/play to avoid diffing across boundaries
        # Note: This relies on 'x' and 'y' being numeric. 'standardize_columns' handles this mostly, 
        # but ensure no object types remain for x/y.
        full_week['dx'] = full_week.groupby(['game_id', 'play_id', 'nfl_id'])['x'].diff()
        full_week['dy'] = full_week.groupby(['game_id', 'play_id', 'nfl_id'])['y'].diff()
        
        # 1. Calculate Speed (s)
        # NFL tracking is 10 frames/sec, so dt = 0.1s
        # Speed = Distance / Time
        full_week['s_derived'] = np.sqrt(full_week['dx']**2 + full_week['dy']**2) / 0.1
        
        # 2. Calculate Direction (dir)
        # Angle of movement vector in degrees (0-360)
        # arctan2 returns radians between -pi and pi.
        full_week['dir_rad'] = np.arctan2(full_week['dy'], full_week['dx'])
        full_week['dir_derived'] = np.degrees(full_week['dir_rad'])
        
        # Convert to 0-360 range (standard math: 0 is East, 90 is North)
        # NFL 'dir' is usually 0=North, 90=East (Clockwise). 
        # Standard Math 'dir' is 0=East, 90=North (Counter-Clockwise).
        # Transformation: NFL_Dir = (90 - Math_Dir) % 360
        full_week['dir_derived_nfl'] = (90 - full_week['dir_derived']) % 360
        
        # 3. Impute Missing Values
        # Only overwrite if original is null
        if 's' not in full_week.columns: full_week['s'] = np.nan
        if 'dir' not in full_week.columns: full_week['dir'] = np.nan
        if 'o' not in full_week.columns: full_week['o'] = np.nan # Start with empty 'o' if missing
        
        full_week['s'] = full_week['s'].fillna(full_week['s_derived'])
        full_week['dir'] = full_week['dir'].fillna(full_week['dir_derived_nfl'])
        
        # 4. Orientation (o) Logic
        # If moving fast (> 2 yds/s), assume o ≈ dir
        mask_fast = full_week['s'] > 2.0
        full_week.loc[mask_fast & full_week['o'].isna(), 'o'] = full_week.loc[mask_fast, 'dir']
        
        # If moving slow/stopped, forward fill last known orientation
        # (Players turn heads slower than they cut)
        full_week['o'] = full_week.groupby(['game_id', 'play_id', 'nfl_id'])['o'].ffill()
        
        # Cleanup temporary columns
        full_week = full_week.drop(columns=['dx', 'dy', 's_derived', 'dir_rad', 'dir_derived', 'dir_derived_nfl'])
        # ---------------------------------------------------------------

        final_cols = [c for c in self.keep_cols if c in full_week.columns]
        full_week = full_week[final_cols]
        
        # Deduplication: keep last (post-throw) if overlap
        full_week = full_week.drop_duplicates(subset=['game_id', 'play_id', 'nfl_id', 'frame_id'], keep='last')
        full_week = full_week.sort_values(['game_id', 'play_id', 'frame_id'])

        # Add has_gap column
        full_week['has_gap'] = full_week.apply(lambda row: play_gap_info.get((row['game_id'], row['play_id']), False), axis=1)

        # Check for missing metadata in critical columns
        critical_cols = ['player_name', 'player_position', 'player_role', 's', 'a', 'dir', 'o']
        def missing_metadata(row):
            return any(pd.isnull(row.get(col)) or row.get(col) == '' for col in critical_cols if col in full_week.columns)
        full_week['missing_metadata'] = full_week.apply(missing_metadata, axis=1)

        return full_week

    def run(self):
        """Runs the full ETL pipeline across all available weeks and saves the processed master file."""
        context_df, valid_keys = self.get_valid_plays_lookup()
        input_files = sorted(glob.glob(os.path.join(self.input_dir, 'input_2023_w*.csv')))
        output_files = glob.glob(os.path.join(self.input_dir, 'output_2023_w*.csv'))
        output_map = {re.search(r'w(\d{2})', f).group(1): f for f in output_files if re.search(r'w(\d{2})', f)}
        processed_data = []
        for input_f in input_files:
            week_match = re.search(r'w(\d{2})', input_f)
            if not week_match:
                continue
            week_num = week_match.group(1)
            output_f = output_map.get(week_num, None)
            week_df = self.process_week_data(week_num, input_f, output_f, valid_keys, context_df)
            if not week_df.empty:
                processed_data.append(week_df)
            gc.collect()
        if processed_data:
            master_df = pd.concat(processed_data, ignore_index=True)
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            master_df.to_csv(self.output_file, index=False)


if __name__ == '__main__':
    etl = ZoneCoverageETL()
    etl.run()