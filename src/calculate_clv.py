import pandas as pd
import numpy as np
import os
from dataclasses import dataclass

@dataclass
class Config:
    """Centralized configuration based on EDA findings."""
    MASTER_FILE: str = 'data/processed/master_zone_tracking.csv'
    EXPORT_STATS: str = 'src/clv_data_export.csv'
    EXPORT_CACHE: str = 'src/animation_cache.csv'
    
    # Timeline
    MIN_POST_THROW_FRAMES: int = 5   # 0.5s min to measure reaction
    PRE_THROW_WINDOW: int = 15       # 1.5s context
    
    # Physics Thresholds
    PUPPETEER_ANGLE: float = 60.0    # Vision cone degrees
    DECOY_SPEED: float = 2.5         # Min speed to be a route runner (yds/s)
    GRAVITY_RADIUS: float = 10.0     # Radius of influence (yards)
    
    # Scoring
    ELITE_CLV: float = 1.5           # Threshold for highlight reels
    MAX_CACHE_SIZE: int = 300        # Max global clips to save

config = Config()


class PhysicsEngine:
    """Handles pure vector math and geometric calculations."""
    
    @staticmethod
    def calculate_clv(defender_vec, ideal_vec):
        ideal_norm = np.linalg.norm(ideal_vec) + 1e-9
        u_ideal = ideal_vec / ideal_norm
        closing_speed = np.dot(defender_vec, u_ideal)
        return -1 * closing_speed

    @staticmethod
    def get_movement_vector(speed, direction_deg):
        """Converts NGS speed/direction (0=North, CW) to Cartesian vector."""
        if pd.isna(direction_deg): return None # Return None to trigger fallback
        dir_rad = np.radians(90 - direction_deg)
        return np.array([speed * np.cos(dir_rad), speed * np.sin(dir_rad)])

    @staticmethod
    def get_vector_from_points(p1, p2):
        """Calculates normalized vector between two points (p2 - p1)."""
        vec = np.array([p2[0] - p1[0], p2[1] - p1[1]])
        norm = np.linalg.norm(vec)
        if norm < 0.01: return None # No movement
        return vec / norm

    @staticmethod
    def get_angle_difference(angle1, angle2):
        """Calculates smallest difference between two angles."""
        diff = abs(angle1 - angle2) % 360
        return min(diff, 360 - diff)


class PlayAnalyzer:
    """
    Encapsulates all logic for a single play.
    Extracts stats, identifies roles, and determines causality.
    """
    def __init__(self, play_df, game_id, play_id):
        self.df = play_df
        self.gid = game_id
        self.pid = play_id
        
        # Lazy loaded properties
        self.ball_land = None
        self.pre_throw = None
        self.start_frame = None
        self.qb = None
        self.victim = None
        self.target = None
        self.valid = False

        self._validate_and_setup()

    def _validate_and_setup(self):
        """Checks if play has necessary data (Ball landing, QB, Phase labels)."""
        if 'ball_land_x' not in self.df.columns: return
        
        # 1. Ball Landing
        bx = self.df['ball_land_x'].iloc[0]
        by = self.df['ball_land_y'].iloc[0]
        if pd.isna(bx): return
        self.ball_land = np.array([bx, by])

        # 2. Pre-Throw Phase
        self.pre_throw = self.df[self.df['phase'] == 'pre_throw']
        if self.pre_throw.empty: return
        
        last_frame = self.pre_throw['frame_id'].max()
        window_start = last_frame - 10
        
        # 3. Valid Window
        self.window = self.pre_throw[self.pre_throw['frame_id'] >= window_start]
        if self.window.empty: return
        
        # 4. Identify Key Players
        start_slice = self.window[self.window['frame_id'] == window_start]
        
        # Find QB
        qb_row = start_slice[start_slice['player_role'] == 'Passer']
        if qb_row.empty: return
        self.qb = qb_row.iloc[0]
        
        # Checkdown Filter (> 8 yards)
        if (self.ball_land[0] - self.qb['x']) < 8.0: return

        # Find Victim (Nearest Defender)
        defs = start_slice[start_slice['player_role'] == 'Defensive Coverage'].copy()
        if defs.empty: return
        
        # Vectorized distance calculation
        dists = np.sqrt((defs['x'] - bx)**2 + (defs['y'] - by)**2)
        self.victim = defs.loc[dists.idxmin()]
        
        # Find Target
        tgt = start_slice[start_slice['player_role'] == 'Targeted Receiver']
        self.target = tgt.iloc[0] if not tgt.empty else None
        
        self.valid = True

    def calculate_metrics(self):
        """Main method to compute CLV, Logic, and BIA stats."""
        if not self.valid: return None

        # 1. Pre-Throw CLV (The Void)
        victim_window = self.window[self.window['nfl_id'] == self.victim['nfl_id']]
        if victim_window.empty: return None
        
        clv_values = []
        for _, row in victim_window.iterrows():
            move_vec = PhysicsEngine.get_movement_vector(row['s'], row['dir'])
            ideal_vec = self.ball_land - np.array([row['x'], row['y']])
            clv_values.append(PhysicsEngine.calculate_clv(move_vec, ideal_vec))
        
        avg_clv = np.mean(clv_values)

        # 2. Causality (Who did it?)
        cause, decoy = self._determine_cause(self.victim)

        # 3. Post-Throw Metrics (Ball In Air)
        bia_eff, react_delay, rec_tax = self._analyze_ball_in_air()

        return {
            'game_id': self.gid, 'play_id': self.pid,
            'nfl_id': self.victim['nfl_id'],
            'player_name': self.victim['player_name'],
            'player_position': self.victim['player_position'],
            'qb_name': self.qb['player_name'],
            'target_name': self.target['player_name'] if self.target is not None else "Unknown",
            'decoy_name': decoy,
            'clv': avg_clv,
            'bia_efficiency': bia_eff,
            'reaction_delay': react_delay,
            'recovery_tax': rec_tax,
            'leak_cause': cause,
            'epa': self.df['expected_points_added'].iloc[0],
            'pass_result': self.df['pass_result'].iloc[0]
        }

    def _determine_cause(self, victim_row):
        """Applies Decision Tree Logic: Puppeteer vs Gravity."""
        # A. Puppeteer Check
        vec_to_qb = np.array([self.qb['x'] - victim_row['x'], self.qb['y'] - victim_row['y']])
        angle_to_qb = np.degrees(np.arctan2(vec_to_qb[1], vec_to_qb[0])) % 360
        victim_o = (90 - victim_row['o']) % 360 # Convert to math angle
        
        vision_error = PhysicsEngine.get_angle_difference(victim_o, angle_to_qb)
        
        if vision_error < config.PUPPETEER_ANGLE:
            return 'Puppeteer', None

        # B. Gravity Check
        # Get frame data for potential decoys
        frame_data = self.window[self.window['frame_id'] == victim_row['frame_id']]
        target_id = self.target['nfl_id'] if self.target is not None else -1
        
        decoys = frame_data[
            (frame_data['player_position'].isin(['WR', 'TE', 'RB', 'FB'])) &
            (frame_data['nfl_id'] != target_id) &
            (frame_data['nfl_id'] != self.qb['nfl_id'])
        ]
        
        closest_dist = float('inf')
        best_decoy = None
        
        for _, d_row in decoys.iterrows():
            dist = np.sqrt((d_row['x'] - victim_row['x'])**2 + (d_row['y'] - victim_row['y'])**2)
            if dist < closest_dist:
                closest_dist = dist
                best_decoy = d_row

        if closest_dist < config.GRAVITY_RADIUS and best_decoy['s'] > config.DECOY_SPEED:
            return 'Gravity', best_decoy['player_name']
            
        return 'Unforced Error', None

    def _analyze_ball_in_air(self):
        """Calculates Panic Score. Uses Coordinate Fallback if Direction is missing."""
        throw_frame = self.pre_throw['frame_id'].max()
        
        post_df = self.df[
            (self.df['nfl_id'] == self.victim['nfl_id']) & 
            (self.df['frame_id'] > throw_frame)
        ].sort_values('frame_id').head(15) 
        
        if len(post_df) < config.MIN_POST_THROW_FRAMES:
            return np.nan, np.nan, np.nan

        efficiencies = []
        prev_pos = None

        for _, row in post_df.iterrows():
            curr_pos = np.array([row['x'], row['y']])
            move_vec = None

            # STRATEGY A: Use Sensor 'dir' (High Precision)
            move_vec = PhysicsEngine.get_movement_vector(1.0, row['dir'])
            
            # STRATEGY B: Use Coordinates (Fallback)
            if move_vec is None and prev_pos is not None:
                move_vec = PhysicsEngine.get_vector_from_points(prev_pos, curr_pos)
            
            # Update history
            prev_pos = curr_pos
            
            # If we still have no vector (e.g. first frame was NaN), skip
            if move_vec is None: continue

            # Calculate Efficiency
            ideal_vec = self.ball_land - curr_pos
            ideal_norm = np.linalg.norm(ideal_vec) + 1e-9
            eff = np.dot(move_vec, ideal_vec / ideal_norm)
            
            if not np.isnan(eff):
                efficiencies.append(eff)
            
        if not efficiencies: return np.nan, np.nan, np.nan

        avg_eff = np.mean(efficiencies)
        
        delays = [i for i, eff in enumerate(efficiencies) if eff > 0.5]
        reaction_delay = delays[0] * 0.1 if delays else len(post_df) * 0.1
        
        # Recovery Tax (Distance)
        start = post_df.iloc[0]
        end = post_df.iloc[-1]
        dist_start = np.linalg.norm(self.ball_land - np.array([start['x'], start['y']]))
        dist_end = np.linalg.norm(self.ball_land - np.array([end['x'], end['y']]))
        rec_tax = 8.0 - ((dist_start - dist_end) * (10.0 / len(post_df)))
        
        return avg_eff, reaction_delay, rec_tax

    def get_clip_data(self):
        """Returns the dataframe slice for animation if valid."""
        if not self.valid: return None
        # Pad with some context before/after
        last_pre = self.pre_throw['frame_id'].max()
        start = int(last_pre - 15)
        end = int(last_pre + 15)
        
        clip = self.df[(self.df['frame_id'] >= start) & (self.df['frame_id'] <= end)].copy()
        
        # Sanitize IDs immediately for Plotly
        clip['nfl_id'] = pd.to_numeric(clip['nfl_id'], errors='coerce').fillna(-1).astype(int).astype(str)
        return clip


class CacheManager:
    """Handles the selection of 'Must Save' clips vs 'Nice to Have'."""
    
    @staticmethod
    def export_cache(results_df, clip_buffer):
        if results_df.empty: return

        print("Selecting VIP Highlights...")
        vip_keys = set()

        # Helper to extract best reps
        def add_bests(df_subset, group_col, sort_col='clv', ascending=False):
            if df_subset.empty: return
            bests = df_subset.sort_values(sort_col, ascending=ascending).drop_duplicates(group_col)
            for _, row in bests.iterrows():
                key = (row['game_id'], row['play_id'])
                if key in clip_buffer:
                    vip_keys.add(key)
                    # Tag metadata for debugging/sorting
                    clip_buffer[key]['highlight_type'] = f"VIP {group_col}"

        # 1. VIPs: Best QBs, Decoys, Worst Victims
        add_bests(results_df[results_df['leak_cause'] == 'Puppeteer'], 'qb_name')
        if 'decoy_name' in results_df.columns:
            add_bests(results_df[results_df['leak_cause'] == 'Gravity'], 'decoy_name')
        add_bests(results_df, 'player_name') # Victim Worst Rep

        # 2. Backfill with Global Top Scores
        # Sort buffer keys by their CLV score
        sorted_keys = sorted(
            clip_buffer.keys(), 
            key=lambda k: clip_buffer[k]['clv_score'].iloc[0] if 'clv_score' in clip_buffer[k] else 0, 
            reverse=True
        )

        for k in sorted_keys:
            if len(vip_keys) >= config.MAX_CACHE_SIZE: break
            if k not in vip_keys:
                vip_keys.add(k)
                clip_buffer[k]['highlight_type'] = 'Global Top'

        # 3. Concatenate and Save
        print(f"Exporting {len(vip_keys)} unique clips...")
        final_clips = [clip_buffer[k] for k in vip_keys if k in clip_buffer]
        
        if final_clips:
            cache_df = pd.concat(final_clips)
            cache_df.to_csv(config.EXPORT_CACHE, index=False)
            print(f"✅ Saved Animation Cache to {config.EXPORT_CACHE}")
        else:
            print("⚠️ No clips met criteria.")


def main():
    if not os.path.exists(config.MASTER_FILE):
        print(f"ERROR: {config.MASTER_FILE} not found.")
        return

    print(f"Loading {config.MASTER_FILE}...")
    df = pd.read_csv(config.MASTER_FILE, low_memory=False)
    
    # Ensure coordinates and direction are floats, or math will fail
    cols_to_fix = ['x', 'y', 's', 'a', 'dis', 'o', 'dir', 'ball_land_x', 'ball_land_y']
    for c in cols_to_fix:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
            
    results = []
    clip_buffer = {} 

    print("Running Physics Engine...")
    
    # Iterate through every play
    for (gid, pid), play_data in df.groupby(['game_id', 'play_id']):
        
        # Instantiate Analyzer
        analyzer = PlayAnalyzer(play_data, gid, pid)
        
        # Calculate Logic
        metrics = analyzer.calculate_metrics()
        
        if not metrics:
            continue

        results.append(metrics)
        
        # Buffer potential highlights
        # We save anything positive; CacheManager filters it later
        if metrics['clv'] > 0.0:
            clip = analyzer.get_clip_data()
            if clip is not None:
                # Inject score for sorting later
                clip['clv_score'] = metrics['clv']
                clip['target_id'] = analyzer.target['nfl_id'] if analyzer.target is not None else -1
                clip_buffer[(gid, pid)] = clip

    # Export Stats
    results_df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(config.EXPORT_STATS), exist_ok=True)
    
    if not results_df.empty:
        print(f"Calculated metrics for {len(results_df)} plays.")
        results_df.to_csv(config.EXPORT_STATS, index=False)
        print(f"✅ Saved Stats to {config.EXPORT_STATS}")
        
        # Export Cache
        CacheManager.export_cache(results_df, clip_buffer)
    else:
        print("❌ No valid plays found.")

if __name__ == '__main__':
    main()