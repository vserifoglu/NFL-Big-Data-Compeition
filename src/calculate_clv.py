import pandas as pd
import numpy as np
import os
from dataclasses import dataclass

@dataclass
class Config:
    """
    Centralized configuration based on Data-Driven Validation (EDA).
    
    Key Metrics Source:
    - PRE/POST WINDOW (15): Volatility analysis shows defender vectors degrade after 1.5s.
    - PANIC THRESHOLD (0.5): Efficiency distribution bimodal split point.
    - GRAVITY RADIUS (10.0): Completion % drops to league average beyond this distance.
    - BENCHMARK SPEED (7.89): 90th percentile of defender recovery speeds.
    """
    MASTER_FILE: str = 'data/processed/master_zone_tracking.csv'
    EXPORT_STATS: str = 'src/clv_data_export.csv'
    EXPORT_CACHE: str = 'src/animation_cache.csv'
    
    # Timeline Parameters
    MIN_POST_THROW_FRAMES: int = 5   # Min 0.5s to measure reaction
    PRE_THROW_WINDOW: int = 15       # 1.5s context window (Valid Manipulation)
    POST_THROW_WINDOW: int = 15      # 1.5s reaction window (Valid Recovery)
    FRAME_DURATION: float = 0.1      # NGS Standard
    
    # Physics Thresholds
    PUPPETEER_ANGLE: float = 70.0    # Vision cone (Std Dev < 15deg)
    DECOY_SPEED: float = 2.5         # Route running speed floor (Valley at 2.5)
    GRAVITY_RADIUS: float = 5.0     # Influence radius (Completion % Dropoff)
    MIN_AIR_YARDS: float = 8.0       # Filter out screens/checkdowns
    
    # Scoring & Benchmarks
    ELITE_CLV: float = 3.0           # Significant momentum shift (>15% max speed)
    PANIC_THRESHOLD: float = 0.5     # Efficiency Score < 0.5 = Panic
    BENCHMARK_SPEED: float = 7.89    # 90th percentile of defender pursuit speed
    MAX_CACHE_SIZE: int = 300        # Max highlights to save

config = Config()


class PhysicsEngine:
    """Stateless utility for vector mathematics."""
    
    @staticmethod
    def calculate_clv(defender_vec, ideal_vec):
        """Calculates Closing Line Velocity: -1 * (Vel · Ideal_Unit)."""
        ideal_norm = np.linalg.norm(ideal_vec) + 1e-9
        u_ideal = ideal_vec / ideal_norm
        closing_speed = np.dot(defender_vec, u_ideal)
        return -1 * closing_speed

    @staticmethod
    def get_movement_vector(speed, direction_deg):
        """Converts NGS speed/direction to Cartesian vector."""
        # Note: We assume 'speed' and 'direction' are pre-filled/healed by ETL
        if pd.isna(direction_deg) or pd.isna(speed): return np.array([0.0, 0.0])
        
        # Convert NFL Compass (0=N, CW) to Math (0=E, CCW) not strictly needed 
        # if we just need relative vectors, but consistent radians are key.
        # Standard NGS: 0=North (Y+), 90=East (X+)
        dir_rad = np.radians(90 - direction_deg)
        return np.array([speed * np.cos(dir_rad), speed * np.sin(dir_rad)])

    @staticmethod
    def get_angle_difference(angle1, angle2):
        """Calculates smallest difference between two angles."""
        diff = abs(angle1 - angle2) % 360
        return min(diff, 360 - diff)


class PlayAnalyzer:
    """Analyzes a single play for voids, causality, and panic."""
    
    def __init__(self, play_df, game_id, play_id):
        self.df = play_df
        self.gid = game_id
        self.pid = play_id
        self.valid = False
        self.air_yards = 0
        self._setup_play_context()

    def _setup_play_context(self):
        """Extracts key actors and validates data availability."""
        if 'ball_land_x' not in self.df.columns: return
        
        # 1. Ball Coordinates
        bx = self.df['ball_land_x'].iloc[0]
        by = self.df['ball_land_y'].iloc[0]
        if pd.isna(bx): return
        self.ball_land = np.array([bx, by])

        # 2. Phases & Windows
        self.pre_throw = self.df[self.df['phase'] == 'pre_throw']
        if self.pre_throw.empty: return
        
        last_frame = self.pre_throw['frame_id'].max()
        
        # Validated: 1.5s window captures the 'Action' phase of manipulation
        window_start = last_frame - config.PRE_THROW_WINDOW 
        
        self.window = self.pre_throw[self.pre_throw['frame_id'] >= window_start]
        if self.window.empty: return
        
        # 3. Actors (QB, Victim, Target)
        snapshot = self.window[self.window['frame_id'] == window_start]
        if snapshot.empty: snapshot = self.window.iloc[0:1]
        
        qb_row = snapshot[snapshot['player_role'] == 'Passer']
        if qb_row.empty: return
        self.qb = qb_row.iloc[0]
        
        # Tactical Filter: Air Yards
        self.air_yards = self.ball_land[0] - self.qb['x']
        if self.air_yards < config.MIN_AIR_YARDS: return

        # Find Victim (Nearest Defender)
        defs = snapshot[snapshot['player_role'] == 'Defensive Coverage'].copy()
        if defs.empty: return
        
        dists = np.sqrt((defs['x'] - bx)**2 + (defs['y'] - by)**2)
        self.victim = defs.loc[dists.idxmin()]
        
        # Find Target
        tgt = snapshot[snapshot['player_role'] == 'Targeted Receiver']
        self.target = tgt.iloc[0] if not tgt.empty else None
        
        self.valid = True

    def calculate_metrics(self):
        """Runs the physics pipeline."""
        if not self.valid: return None

        # 1. Pre-Throw Voids (CLV)
        avg_clv = self._calculate_pre_throw_clv()
        if avg_clv is None: return None

        # 2. Causality (Puppeteer / Gravity / Dual Threat)
        cause, decoy = self._determine_cause(self.victim)

        # 3. Post-Throw Panic (Ball-In-Air)
        bia_eff, delay, rec_tax = self._analyze_ball_in_air()

        return {
            'game_id': self.gid, 'play_id': self.pid,
            'nfl_id': self.victim['nfl_id'],
            'player_name': self.victim['player_name'],
            'player_position': self.victim['player_position'],
            'qb_name': self.qb['player_name'],
            'target_name': self.target['player_name'] if self.target is not None else "Unknown",
            'decoy_name': decoy,
            'air_yards': self.air_yards,
            'clv': avg_clv,
            'bia_efficiency': bia_eff,
            'reaction_delay': delay,
            'recovery_tax': rec_tax,
            'leak_cause': cause,
            'epa': self.df['expected_points_added'].iloc[0],
            'pass_result': self.df['pass_result'].iloc[0]
        }

    def _calculate_pre_throw_clv(self):
        """Calculates avg CLV during the trick window."""
        victim_frames = self.window[self.window['nfl_id'] == self.victim['nfl_id']]
        if victim_frames.empty: return None
        
        clv_vals = []
        for _, row in victim_frames.iterrows():
            # Note: Relying on ETL-healed 's' and 'dir'
            move_vec = PhysicsEngine.get_movement_vector(row['s'], row['dir'])
            
            ideal_vec = self.ball_land - np.array([row['x'], row['y']])
            clv_vals.append(PhysicsEngine.calculate_clv(move_vec, ideal_vec))

        return np.mean(clv_vals) if clv_vals else None

    def _determine_cause(self, victim_row):
        """Logic: QB Eyes (Puppeteer), Route Gravity, or Dual Threat."""
        causes = []
        decoy_name = None

        # A. Puppeteer Check
        vec_to_qb = np.array([self.qb['x'] - victim_row['x'], self.qb['y'] - victim_row['y']])
        angle_to_qb = np.degrees(np.arctan2(vec_to_qb[1], vec_to_qb[0])) % 360
        
        # NFL Orientation is 0=North (Y+), 90=East (X+)
        # Math Angle is 0=East, 90=North
        # We convert NFL 'o' to Math Angle for comparison, or vice versa. 
        # Here we convert Victim 'o' to math angle to match arctan2.
        victim_math_angle = (90 - victim_row['o']) % 360
        
        vision_error = PhysicsEngine.get_angle_difference(victim_math_angle, angle_to_qb)
        
        if vision_error < config.PUPPETEER_ANGLE:
            causes.append('Puppeteer')

        # B. Gravity Check
        frame_data = self.window[self.window['frame_id'] == victim_row['frame_id']]
        target_id = self.target['nfl_id'] if self.target is not None else -1
        
        decoys = frame_data[
            (frame_data['player_position'].isin(['WR', 'TE', 'RB', 'FB'])) &
            (frame_data['nfl_id'] != target_id) &
            (frame_data['nfl_id'] != self.qb['nfl_id']) &
            (frame_data['s'] > config.DECOY_SPEED)
        ]
        
        if not decoys.empty:
            dists = np.sqrt((decoys['x'] - victim_row['x'])**2 + (decoys['y'] - victim_row['y'])**2)
            min_dist_idx = dists.idxmin()
            
            # Validated: 10.0 yard radius of influence
            if dists[min_dist_idx] < config.GRAVITY_RADIUS:
                causes.append('Gravity')
                decoy_name = decoys.loc[min_dist_idx]['player_name']

        # C. Classification
        if 'Puppeteer' in causes and 'Gravity' in causes:
            return 'Dual Threat', decoy_name
        elif 'Puppeteer' in causes:
            return 'Puppeteer', None
        elif 'Gravity' in causes:
            return 'Gravity', decoy_name
        else:
            return 'Unforced Error', None

    def _analyze_ball_in_air(self):
        """Calculates Panic Scores on Pre-Processed Data."""
        throw_frame = self.pre_throw['frame_id'].max()
        
        # 1. WINDOW FILTER (15 Frames)
        post_df = self.df[
            (self.df['nfl_id'] == self.victim['nfl_id']) & 
            (self.df['frame_id'] > throw_frame)
        ].sort_values('frame_id').head(config.POST_THROW_WINDOW) 
        
        # Min Frames Check
        if len(post_df) < config.MIN_POST_THROW_FRAMES:
            return np.nan, np.nan, np.nan

        # 2. COMPETITIVENESS FILTER (5 Yards)
        start = post_df.iloc[0]
        dist_to_ball = np.linalg.norm(self.ball_land - np.array([start['x'], start['y']]))
        if dist_to_ball > config.GRAVITY_RADIUS:
            return np.nan, np.nan, np.nan

        efficiencies = []
        
        for _, row in post_df.iterrows():
            curr_pos = np.array([row['x'], row['y']])
            
            # Trust the ETL: 's' and 'dir' are guaranteed to be populated
            move_vec = PhysicsEngine.get_movement_vector(row['s'], row['dir'])
            
            # Efficiency Dot Product
            ideal_vec = self.ball_land - curr_pos
            ideal_norm = np.linalg.norm(ideal_vec) + 1e-9
            eff = np.dot(move_vec, ideal_vec / ideal_norm)
            
            if not np.isnan(eff): efficiencies.append(eff)
            
        if not efficiencies: return np.nan, np.nan, np.nan

        avg_eff = np.mean(efficiencies)
        
        # 3. REACTION DELAY (Threshold: 0.5)
        delays = [i for i, eff in enumerate(efficiencies) if eff > config.PANIC_THRESHOLD]
        delay_seconds = (delays[0] * config.FRAME_DURATION) if delays else (len(post_df) * config.FRAME_DURATION)
        
        # 4. RECOVERY TAX (Benchmark: 7.89)
        final_pos = np.array([post_df.iloc[-1]['x'], post_df.iloc[-1]['y']])
        
        dist_covered = dist_to_ball - np.linalg.norm(self.ball_land - final_pos)
        
        max_possible_dist = config.BENCHMARK_SPEED * (len(post_df) * config.FRAME_DURATION)
        rec_tax = max_possible_dist - dist_covered
        
        return avg_eff, delay_seconds, rec_tax

    def get_clip_data(self):
        """Extracts animation clip."""
        if not self.valid: return None
        end_frame = self.pre_throw['frame_id'].max()
        clip = self.df[(self.df['frame_id'] >= end_frame - 15) & (self.df['frame_id'] <= end_frame + 15)].copy()
        if 'nfl_id' in clip.columns:
            clip['nfl_id'] = pd.to_numeric(clip['nfl_id'], errors='coerce').fillna(-1).astype(int).astype(str)
        return clip


class CacheManager:
    """Manages 'VIP' Animation Cache logic."""
    
    @staticmethod
    def export(results_df, clip_buffer):
        if results_df.empty: return
        print("Selecting VIP Highlights...")
        vip_keys = set()

        def add_bests(subset, group_col):
            if subset.empty: return
            bests = subset.sort_values('clv', ascending=False).drop_duplicates(group_col)
            for _, row in bests.iterrows():
                key = (row['game_id'], row['play_id'])
                if key in clip_buffer:
                    vip_keys.add(key)
                    clip_buffer[key]['highlight_type'] = f"VIP {group_col}"

        # Save Best Reps
        add_bests(results_df[results_df['leak_cause'] == 'Puppeteer'], 'qb_name')
        add_bests(results_df[results_df['leak_cause'] == 'Dual Threat'], 'qb_name')
        if 'decoy_name' in results_df.columns:
            add_bests(results_df[results_df['leak_cause'] == 'Gravity'], 'decoy_name')
        
        # Save Worst Reps for Victims
        add_bests(results_df, 'player_name')

        # Fill Rest with Top Scores
        sorted_keys = sorted(
            clip_buffer.keys(), 
            key=lambda k: clip_buffer[k]['clv_score'].iloc[0], 
            reverse=True
        )
        
        for k in sorted_keys:
            if len(vip_keys) >= config.MAX_CACHE_SIZE: break
            if k not in vip_keys:
                vip_keys.add(k)
                clip_buffer[k]['highlight_type'] = 'Global Top'

        print(f"Exporting {len(vip_keys)} clips...")
        final_clips = [clip_buffer[k] for k in vip_keys if k in clip_buffer]
        if final_clips:
            pd.concat(final_clips).to_csv(config.EXPORT_CACHE, index=False)
            print(f"✅ Saved Cache to {config.EXPORT_CACHE}")


def main():
    if not os.path.exists(config.MASTER_FILE):
        print(f"ERROR: {config.MASTER_FILE} missing. Run ETL pipeline first.")
        return

    print(f"Loading {config.MASTER_FILE}...")
    df = pd.read_csv(config.MASTER_FILE, low_memory=False)
    
    for c in ['x', 'y', 's', 'dir', 'o', 'ball_land_x', 'ball_land_y']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')

    results = []
    clip_buffer = {}

    print("Running Physics Engine...")
    for (gid, pid), play_data in df.groupby(['game_id', 'play_id']):
        analyzer = PlayAnalyzer(play_data, gid, pid)
        metrics = analyzer.calculate_metrics()
        
        if metrics:
            results.append(metrics)
            if metrics['clv'] > config.ELITE_CLV:
                clip = analyzer.get_clip_data()
                if clip is not None:
                    clip['clv_score'] = metrics['clv']
                    clip['target_id'] = analyzer.target['nfl_id'] if analyzer.target is not None else -1
                    clip_buffer[(gid, pid)] = clip

    res_df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(config.EXPORT_STATS), exist_ok=True)
    
    if not res_df.empty:
        print(f"Metrics calculated for {len(res_df)} plays.")
        res_df.to_csv(config.EXPORT_STATS, index=False)
        print(f"✅ Stats saved to {config.EXPORT_STATS}")
        CacheManager.export(res_df, clip_buffer)
    else:
        print("❌ No results.")

if __name__ == '__main__':
    main()