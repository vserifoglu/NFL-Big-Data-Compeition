import pandas as pd
import numpy as np

# TODO: define hardcode nubmers. 

class StoryDataEngine:
    def __init__(self, summary_path: str, frames_path: str, seed=42):
        self.summary_df = pd.read_csv(summary_path)
        self.frames_path = frames_path
        self.seed = seed
        
    def cast_archetypes(self):
        """
        UPDATED: Selects candidates based on the new VIS thresholds.
        Returns keys: 'The Eraser', 'The Rally', 'The Blanket', 'The Liability'
        """
        df = self.summary_df
        
        # THE ERASER (Elite Recovery)
        # Criteria: Deep start (>10), Massive VIS (>3)
        eraser_pool = df[
            (df['p_dist_at_throw'] > 10) & 
            (df['vis_score'] > 3.0) & 
            (df['dist_at_arrival'] < 4) 
        ]
        eraser = self._select_candidate(eraser_pool, sort_col='vis_score', ascending=False)
        
        # THE RALLY (Standard Zone / The Blob)
        # Criteria: Deep start (>8), Moderate VIS (0.5 to 2.0)
        rally_pool = df[
            (df['p_dist_at_throw'] > 8) & 
            (df['vis_score'].between(0.5, 2.0)) &
            (df['dist_at_arrival'] < 8)
        ]
        rally = self._select_candidate(rally_pool, sort_col='vis_score', ascending=False)
        
        # THE BLANKET (Maintenance)
        # Criteria: Tight start (<3), VIS near zero (-0.5 to 0.5)
        blanket_pool = df[
            (df['p_dist_at_throw'] < 3) & 
            (df['vis_score'].between(-0.5, 0.5)) &
            (df['dist_at_arrival'] < 3)
        ]
        blanket = self._select_candidate(blanket_pool, sort_col='dist_at_arrival', ascending=True)
        
        # THE LIABILITY (True Failure)
        # Criteria: Any start, Negative VIS (Lost Ground)
        liability_pool = df[
            (df['vis_score'] < -1.0) & 
            (df['dist_at_arrival'] > 2.0)
        ]
        liability = self._select_candidate(liability_pool, sort_col='vis_score', ascending=True)

        return {
            'The Eraser': self._extract_meta(eraser, "The Eraser (Elite)"),
            'The Rally': self._extract_meta(rally, "The Rally (Zone)"),
            'The Blanket': self._extract_meta(blanket, "The Blanket (Lockdown)"),
            'The Liability': self._extract_meta(liability, "The Liability (Lost Gap)")
        }

    def _select_candidate(self, df, sort_col, ascending, top_n=1):
        if df.empty: return pd.DataFrame()
        sorted_df = df.sort_values(sort_col, ascending=ascending)
        df = sorted_df.head(top_n)
        print(df.get("player_name", "Unknown Player"))
        return df

    def _extract_meta(self, row, label):
        if row.empty: return None
        return {
            'game_id': int(row.iloc[0]['game_id']),
            'play_id': int(row.iloc[0]['play_id']),
            'nfl_id': float(row.iloc[0]['nfl_id']),
            'player_name': str(row.iloc[0].get('player_name', 'Unknown')),
            'vis_score': float(row.iloc[0]['vis_score']),
            'label': label
        }

    def get_position_contrast(self, position='FS', min_snaps=15):
        """
        Apple-to-apple comparison: Top vs Bottom player for the same position.
        
        1. Ranks players by avg CEOE within the position
        2. Top player → their best VIS play (biggest close)
        3. Bottom player → their worst VIS play (biggest loss)
        """
        df = self.summary_df
        pos_df = df[df['player_position'] == position].copy()
        
        if pos_df.empty:
            print(f"No plays found for position: {position}")
            return {'top': None, 'bottom': None}
        
        # Rank players by average CEOE
        player_ranks = pos_df.groupby('nfl_id').agg(
            player_name=('player_name', 'first'),
            avg_ceoe=('ceoe_score', 'mean'),
            snaps=('play_id', 'count')
        ).reset_index()
        
        # Filter for minimum snaps
        qualified = player_ranks[player_ranks['snaps'] >= min_snaps]
        
        if len(qualified) < 2:
            print(f"Not enough qualified players for {position} (need 2, have {len(qualified)})")
            return {'top': None, 'bottom': None}
        
        top_player = qualified.nlargest(1, 'avg_ceoe').iloc[0]
        bottom_player = qualified.nsmallest(1, 'avg_ceoe').iloc[0]
        
        top_id = top_player['nfl_id']
        bottom_id = bottom_player['nfl_id']

        # Find their best/worst plays
        top_plays = pos_df[pos_df['nfl_id'] == top_id]
        bottom_plays = pos_df[pos_df['nfl_id'] == bottom_id]
        
        # Top player's BEST play (highest VIS = biggest close)
        top_best = top_plays.nlargest(1, 'vis_score')
        
        # Bottom player's WORST play (lowest VIS = biggest loss)
        bottom_worst = bottom_plays.nsmallest(1, 'vis_score')
        
        print(f"Top's best play: VIS = {top_best.iloc[0]['vis_score']:.2f}")
        print(f"Bottom's worst play: VIS = {bottom_worst.iloc[0]['vis_score']:.2f}")
        
        return {
            'top': self._extract_meta(top_best, f"Top {position} Eraser"),
            'bottom': self._extract_meta(bottom_worst, f"Bottom {position} Eraser")
        }

    def get_archetype_contrast(self, min_snaps=15):
        """
        Role contrast: Top FS Eraser vs Top CB Lockdown.
        
        Shows WHY different positions should be graded differently:
        - FS: Closes big gaps (high VIS)
        - CB: Stays tight (low dist_at_arrival)
        """
        df = self.summary_df
        
        fs_df = df[df['player_position'] == 'FS'].copy()
        fs_ranks = fs_df.groupby('nfl_id').agg(
            player_name=('player_name', 'first'),
            avg_ceoe=('ceoe_score', 'mean'),
            snaps=('play_id', 'count')
        ).reset_index()
        fs_qualified = fs_ranks[fs_ranks['snaps'] >= min_snaps]
        
        if fs_qualified.empty:
            print("No qualified FS players")
            return {'eraser': None, 'lockdown': None}
        
        top_fs = fs_qualified.nlargest(1, 'avg_ceoe').iloc[0]
        top_fs_plays = fs_df[fs_df['nfl_id'] == top_fs['nfl_id']]
        eraser_play = top_fs_plays.nlargest(1, 'vis_score')
        
        cb_df = df[df['player_position'] == 'CB'].copy()
        cb_ranks = cb_df.groupby('nfl_id').agg(
            player_name=('player_name', 'first'),
            avg_arrival=('dist_at_arrival', 'mean'),
            snaps=('play_id', 'count')
        ).reset_index()
        cb_qualified = cb_ranks[cb_ranks['snaps'] >= min_snaps]
        
        if cb_qualified.empty:
            print("No qualified CB players")
            return {'eraser': None, 'lockdown': None}
        
        top_cb = cb_qualified.nsmallest(1, 'avg_arrival').iloc[0]  
        top_cb_plays = cb_df[cb_df['nfl_id'] == top_cb['nfl_id']]
        lockdown_play = top_cb_plays.nsmallest(1, 'dist_at_arrival') 

        return {
            'eraser': self._extract_meta(eraser_play, f"Top FS Eraser: {top_fs['player_name']}"),
            'lockdown': self._extract_meta(lockdown_play, f"Top CB Lockdown: {top_cb['player_name']}")
        }

    def get_play_frames(self, play_meta):
        if not play_meta: return pd.DataFrame()
        df = pd.read_csv(self.frames_path)
        return df[(df['game_id'] == play_meta['game_id']) & (df['play_id'] == play_meta['play_id'])].copy()