import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from dataclasses import dataclass

# ==========================================
# CONFIGURATION
# ==========================================
@dataclass
class Config:
    RESULTS_PATH: str = "src/clv_data_export.csv"
    CACHE_PATH: str = "src/animation_cache.csv"
    
    # Visual Mappings for Plotly
    COLOR_MAP = {
        'Football': 'brown', 'Quarterback': 'gold',
        'VICTIM (Leaker)': 'magenta', 'Target (Receiver)': 'lime',
        'Decoy (Gravity)': '#00FFFF', 'Defense': 'red', 'Offense': 'blue'
    }
    SIZE_MAP = {
        'Football': 6, 'Quarterback': 12, 'VICTIM (Leaker)': 16, 
        'Target (Receiver)': 12, 'Decoy (Gravity)': 16, 'Defense': 8, 'Offense': 8
    }
    SYMBOL_MAP = {
        'Football': 'circle', 'Quarterback': 'diamond',
        'VICTIM (Leaker)': 'x', 'Target (Receiver)': 'star',
        'Decoy (Gravity)': 'triangle-up', 'Defense': 'circle', 'Offense': 'circle'
    }

# ==========================================
# DATA SERVICE
# ==========================================
class DataService:
    """Handles data loading, type safety, and aggregation."""
    
    def __init__(self):
        self.results = self._load_csv(Config.RESULTS_PATH)
        self.cache = self._load_csv(Config.CACHE_PATH)
        self._ensure_types()

    def _load_csv(self, path):
        if os.path.exists(path):
            return pd.read_csv(path)
        return pd.DataFrame()

    def _ensure_types(self):
        """Forces string IDs to prevent Plotly animation glitches."""
        if not self.cache.empty and 'nfl_id' in self.cache.columns:
            self.cache['nfl_id'] = pd.to_numeric(self.cache['nfl_id'], errors='coerce').fillna(-1).astype(int).astype(str)

    def get_summary_metrics(self):
        """Calculates dashboard summary stats."""
        if self.results.empty: return None
        avg_clv = self.results['clv'].mean()
        high_leak = self.results[self.results['clv'] > 1.5]
        low_leak = self.results[self.results['clv'] < -0.5]
        
        hl_comp = (high_leak['pass_result'] == 'C').mean() if not high_leak.empty else 0
        ll_comp = (low_leak['pass_result'] == 'C').mean() if not low_leak.empty else 0
        
        return {
            'avg_void': avg_clv,
            'high_leak_comp': hl_comp,
            'low_leak_comp': ll_comp,
            'delta': (hl_comp - ll_comp) * 100
        }

    def get_play_catalog(self):
        """Creates a rich table of available highlights."""
        if self.cache.empty or self.results.empty: return pd.DataFrame()

        available = self.cache[['game_id', 'play_id', 'highlight_type', 'clv_score']].drop_duplicates()
        
        catalog = available.merge(
            self.results[['game_id', 'play_id', 'qb_name', 'player_name', 'decoy_name', 'leak_cause', 'pass_result', 'epa']],
            on=['game_id', 'play_id'],
            how='left'
        )

        def generate_story(row):
            qb = str(row['qb_name']).split()[-1]
            vic = str(row['player_name']).split()[-1]
            cause = row['leak_cause']
            if cause == 'Puppeteer': return f"👀 {qb} looked off {vic}"
            elif cause == 'Gravity':
                decoy = str(row['decoy_name']).split()[-1] if pd.notna(row['decoy_name']) else "Decoy"
                return f"🧲 {decoy} pulled {vic} deep"
            elif cause == 'Dual Threat': return f"🔥 {qb} & Decoy broke {vic}"
            else: return f"⚠️ {vic} blew coverage"

        catalog['The Story'] = catalog.apply(generate_story, axis=1)
        catalog['Score'] = catalog['clv_score'].round(2)
        catalog['Result'] = catalog['pass_result']
        
        display_cols = ['game_id', 'play_id', 'highlight_type', 'Score', 'The Story', 'Result', 'epa']
        return catalog[display_cols].sort_values('Score', ascending=False)

    def get_truth_chart_data(self):
        """Prepares comparison data."""
        df = self.results.copy()
        df['Status'] = df['clv'].apply(lambda x: "Fooled (High Leak)" if x > 1.5 else ("Locked In (Read)" if x < -0.5 else "Neutral"))
        df['is_complete'] = (df['pass_result'] == 'C').astype(int)
        
        stats = df.groupby('Status')['is_complete'].mean().reset_index()
        sort_map = {"Fooled (High Leak)": 0, "Neutral": 1, "Locked In (Read)": 2}
        stats['sort'] = stats['Status'].map(sort_map)
        return stats.sort_values('sort')

    def get_league_scatter_data(self):
        """Returns QB data for the 'Quadrant of Domination'."""
        df = self.results[self.results['leak_cause'] == 'Puppeteer'].copy()
        stats = df.groupby('qb_name').agg(
            Total_Void_Yards=('clv', 'sum'),
            EPA_Per_Play=('epa', 'mean'),
            Plays=('clv', 'count')
        ).reset_index()
        return stats[stats['Plays'] >= 20]

    def get_top_three(self):
        """Returns the #1 player for each category for the 'Hit List'."""
        pup = self.get_puppeteer_stats().iloc[0]
        grav_df = self.get_gravity_stats()
        grav = grav_df.iloc[0] if not grav_df.empty else None
        vic = self.get_victim_stats().iloc[0]
        
        return {
            'puppeteer': (pup['qb_name'], pup['Total_Void_Yards']),
            'gravity': (grav['decoy_name'], grav['Total_EPA_Generated']) if grav is not None else ("N/A", 0),
            'victim': (vic['player_name'], vic['Total_Void_Allowed'])
        }

    def get_completion_by_panic_bucket(self):
        """Returns data for 'The Panic Cliff' bar chart."""
        df = self.results.copy()
        df['Panic_Bucket'] = pd.qcut(df['bia_efficiency'], 4, labels=["Extreme Panic", "High Panic", "Composed", "Locked In"])
        df['is_complete'] = (df['pass_result'] == 'C').astype(int)
        
        stats = df.groupby('Panic_Bucket')['is_complete'].mean().reset_index()
        stats['Completion_Rate'] = stats['is_complete'] * 100
        return stats

    def get_puppeteer_stats(self):
        """Returns QBs ranked by Volume."""
        df = self.results[self.results['leak_cause'] == 'Puppeteer'].copy()
        stats = df.groupby('qb_name').agg(
            Total_Void_Yards=('clv', 'sum'),
            Avg_Void=('clv', 'mean'),
            Plays=('clv', 'count')
        ).reset_index()
        
        # Add 'pass_result' to best reps retrieval
        bests = df.sort_values('clv', ascending=False).drop_duplicates('qb_name')[['qb_name', 'game_id', 'play_id', 'pass_result']]
        return stats.merge(bests, on='qb_name').sort_values('Total_Void_Yards', ascending=False)

    def get_gravity_stats(self):
        """Returns Decoys ranked by EPA."""
        if 'decoy_name' not in self.results.columns: return pd.DataFrame()
        df = self.results[self.results['leak_cause'] == 'Gravity'].copy()
        
        stats = df.groupby('decoy_name').agg(
            Total_EPA_Generated=('epa', 'sum'),
            Avg_Void=('clv', 'mean'),
            Plays=('clv', 'count')
        ).reset_index()
        
        # Add 'pass_result' to best reps retrieval
        bests = df.sort_values('clv', ascending=False).drop_duplicates('decoy_name')[['decoy_name', 'game_id', 'play_id', 'pass_result']]
        return stats.merge(bests, on='decoy_name').sort_values('Total_EPA_Generated', ascending=False)

    def get_victim_stats(self):
        """Returns Defenders ranked by Void Allowed."""
        def calc_panic(x):
            valid = x.dropna()
            if valid.empty: return 0.0
            return max(0.0, min(((1.0 - valid.mean()) / 2.0) * 100, 100.0))

        stats = self.results.groupby(['player_name', 'player_position']).agg(
            Total_Void_Allowed=('clv', 'sum'),
            Times_Fooled=('clv', 'count'),
            Avg_Panic_Score=('bia_efficiency', calc_panic)
        ).reset_index()
        
        # Add 'pass_result' to worst reps retrieval
        worsts = self.results.sort_values('clv', ascending=False).drop_duplicates('player_name')[['player_name', 'game_id', 'play_id', 'nfl_id', 'pass_result']]
        return stats.merge(worsts, on='player_name').sort_values('Total_Void_Allowed', ascending=False)

    def prepare_animation_frame(self, game_id, play_id, victim_id=-1, decoy_name=None):
        """Fetches and formats frame data for plotting."""
        play_data = self.cache[(self.cache['game_id'] == game_id) & (self.cache['play_id'] == play_id)].copy()
        if play_data.empty: return None, None, None

        cols = play_data.columns
        name_col = 'player_name' if 'player_name' in cols else 'displayName'
        if name_col not in cols: name_col = 'nfl_id'
        id_col = 'nfl_id'

        # Statue Logic
        if 'phase' in play_data.columns:
            post_frames = sorted(play_data[play_data['phase'] == 'post_throw']['frame_id'].unique())
            if post_frames:
                pre_ids = set(play_data[play_data['phase'] == 'pre_throw'][id_col].unique())
                post_ids = set(play_data[play_data['phase'] == 'post_throw'][id_col].unique())
                dropout_ids = list(pre_ids - post_ids)
                
                if dropout_ids:
                    last_known = play_data[play_data[id_col].isin(dropout_ids)].sort_values('frame_id').groupby(id_col).tail(1)
                    ghosts = []
                    for _, row in last_known.iterrows():
                        for f in post_frames:
                            g = row.copy()
                            g['frame_id'] = f
                            ghosts.append(g)
                    if ghosts:
                        play_data = pd.concat([play_data, pd.DataFrame(ghosts)], ignore_index=True)

        play_data = play_data.sort_values(['frame_id', id_col])
        play_data = self._apply_visual_roles(play_data, name_col, id_col, victim_id, decoy_name)
        return play_data, name_col, id_col

    def _apply_visual_roles(self, df, name_col, id_col, victim_id, decoy_name):
        """Assigns roles for coloring/sizing."""
        tgt_id = -1
        if 'target_id' in df.columns:
            ts = df['target_id'].dropna().unique()
            if len(ts) > 0: tgt_id = int(ts[0])

        s_vic, s_tgt = str(victim_id), str(tgt_id)
        clean_decoy = str(decoy_name).lower().strip() if decoy_name else None

        def get_role(row):
            pid = str(row[id_col])
            pname = str(row[name_col]).lower().strip()
            
            if 'football' in pname or pid == '999999': return 'Football', ''
            if clean_decoy and clean_decoy in pname: return 'Decoy (Gravity)', f"GRAVITY: {row[name_col]}"
            if pid == s_tgt: return 'Target (Receiver)', f"TARGET: {row[name_col]}"
            if pid == s_vic: return 'VICTIM (Leaker)', f"VICTIM: {row[name_col]}"
            
            pos = str(row.get('position', ''))
            role = str(row.get('player_role', ''))
            if pos == 'QB' or role == 'Passer': return 'Quarterback', f"QB: {row[name_col]}"
            
            side = str(row.get('player_side', '')).lower()
            return ('Defense', '') if side == 'defense' else ('Offense', '')

        roles = df.apply(get_role, axis=1)
        df['visual_role'] = [r[0] for r in roles]
        df['visual_label'] = [r[1] for r in roles]
        df['visual_size'] = df['visual_role'].map(Config.SIZE_MAP).fillna(8)
        return df

# ==========================================
# VISUALIZATION SERVICE
# ==========================================
class VizService:
    """Plotly Factory."""
    
    @staticmethod
    def create_field_animation(df, game_id, play_id, name_col, id_col):
        fig = px.scatter(
            df, x='x', y='y', animation_frame='frame_id', animation_group=id_col,
            color='visual_role', color_discrete_map=Config.COLOR_MAP,
            symbol='visual_role', symbol_map=Config.SYMBOL_MAP,
            size='visual_size', size_max=18,
            text='visual_label', hover_name=name_col,
            range_x=[0, 120], range_y=[0, 53.3],
            title=f"Game {game_id} | Play {play_id}"
        )
        
        if 'ball_land_x' in df.columns:
            bx, by = df['ball_land_x'].iloc[0], df['ball_land_y'].iloc[0]
            fig.add_trace(go.Scatter(
                x=[bx], y=[by], mode='markers', 
                marker=dict(symbol='star-open', size=20, color='yellow'),
                name='Catch Point'
            ))
            
        fig.update_traces(textposition='top center')
        fig.update_layout(height=600)
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 100
        return fig

    @staticmethod
    def create_scatter(df, x, y, title, labels):
        fig = px.scatter(
            df, x=x, y=y, trendline="ols", trendline_color_override="red",
            labels=labels, title=title, opacity=0.3
        )
        if 'bia_efficiency' in y: 
            fig.update_yaxes(autorange="reversed")
        return fig