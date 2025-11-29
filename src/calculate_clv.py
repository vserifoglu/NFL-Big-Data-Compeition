import pandas as pd
import numpy as np
import os

# ==========================================
# CONFIGURATION
# ==========================================
MASTER_FILE = 'data/processed/master_zone_tracking.csv'
EXPORT_STATS = 'src/clv_data_export.csv'
EXPORT_CACHE = 'src/animation_cache.csv'

# We will save specific "Must Have" plays plus the top global highlights
MAX_GLOBAL_HIGHLIGHTS = 300 

def main():
    if not os.path.exists(MASTER_FILE):
        print(f"ERROR: {MASTER_FILE} not found.")
        return

    print(f"Loading {MASTER_FILE}...")
    df = pd.read_csv(MASTER_FILE, low_memory=False)
    
    results = []
    
    # BUFFER: We temporarily store ANY play with a decent score (e.g. > 0.5)
    # We will filter this list strictly at the end based on who makes the "Scouting Report"
    clip_library = {} 

    print("Analyzing Plays...")
    
    for (gid, pid), play_data in df.groupby(['game_id', 'play_id']):
        
        # --- 1. PRE-CHECKS (Same as before) ---
        if 'ball_land_x' not in play_data.columns: continue
        ball_x = play_data['ball_land_x'].iloc[0]
        ball_y = play_data['ball_land_y'].iloc[0]
        if pd.isna(ball_x): continue

        pre_throw = play_data[play_data['phase'] == 'pre_throw']
        if pre_throw.empty: continue
        
        last_frame_pre = pre_throw['frame_id'].max()
        window_start = last_frame_pre - 10
        trick_window = pre_throw[pre_throw['frame_id'] >= window_start]
        if trick_window.empty: continue

        start_frame_data = trick_window[trick_window['frame_id'] == window_start]
        
        qb_row = start_frame_data[start_frame_data['player_role'] == 'Passer']
        if qb_row.empty: continue 
            
        qb_x = qb_row.iloc[0]['x']
        qb_y = qb_row.iloc[0]['y']
        qb_name = qb_row.iloc[0]['player_name']
        
        derived_pass_length = ball_x - qb_x
        if derived_pass_length < 8.0: continue 

        # --- 2. IDENTIFY VICTIM ---
        defenders = start_frame_data[start_frame_data['player_role'] == 'Defensive Coverage']
        if defenders.empty: continue
        
        dists = np.sqrt((defenders['x'] - ball_x)**2 + (defenders['y'] - ball_y)**2)
        subject_idx = dists.idxmin()
        subject_id = defenders.loc[subject_idx, 'nfl_id']
        def_name = defenders.loc[subject_idx, 'player_name']
        def_pos = defenders.loc[subject_idx, 'player_position']
        
        target_row = start_frame_data[start_frame_data['player_role'] == 'Targeted Receiver']
        target_name = target_row.iloc[0]['player_name'] if not target_row.empty else "Unknown"
        target_id = target_row.iloc[0]['nfl_id'] if not target_row.empty else -1

        # --- 3. VISION & CAUSALITY ---
        leak_cause = 'Unforced Error' 
        decoy_name_str = None
        
        def_x, def_y, def_o = defenders.loc[subject_idx, ['x', 'y', 'o']]
        
        vec_qb_deg = np.degrees(np.arctan2(qb_y - def_y, qb_x - def_x)) % 360
        def_o_math = (90 - def_o) % 360
        diff_qb = abs(def_o_math - vec_qb_deg)
        vision_error_qb = min(diff_qb, 360 - diff_qb)
        
        if vision_error_qb < 60: 
            leak_cause = 'Puppeteer'
        else:
            qb_id = qb_row.iloc[0]['nfl_id']
            potential_decoys = start_frame_data[
                (start_frame_data['player_position'].isin(['WR', 'TE', 'RB', 'FB'])) & 
                (start_frame_data['nfl_id'] != target_id) & 
                (start_frame_data['nfl_id'] != qb_id)
            ]
            
            min_dist = float('inf')
            max_speed = 0
            best_decoy_row = None
            
            for _, decoy in potential_decoys.iterrows():
                d_dist = np.sqrt((decoy['x'] - def_x)**2 + (decoy['y'] - def_y)**2)
                if d_dist < min_dist:
                    min_dist = d_dist
                    max_speed = decoy['s']
                    best_decoy_row = decoy
            
            if min_dist < 10.0 and max_speed > 2.0:
                leak_cause = 'Gravity'
                if best_decoy_row is not None:
                    decoy_name_str = best_decoy_row['player_name']

        # --- 4. CALCULATE CLV ---
        subj_window = trick_window[trick_window['nfl_id'] == subject_id].copy()
        if subj_window.empty: continue
        
        dir_rad = np.radians(90 - subj_window['dir'])
        vx = subj_window['s'] * np.cos(dir_rad)
        vy = subj_window['s'] * np.sin(dir_rad)
        dx = ball_x - subj_window['x']
        dy = ball_y - subj_window['y']
        dist = np.sqrt(dx**2 + dy**2) + 1e-6
        closing_speed = (vx * (dx/dist)) + (vy * (dy/dist))
        clv = -1 * closing_speed.mean()

        # --- 5. RECOVERY TAX ---
        recovery_tax = np.nan
        post_throw = play_data[(play_data['phase'] == 'post_throw') & (play_data['nfl_id'] == subject_id)]
        if len(post_throw) >= 10:
            post_throw = post_throw.sort_values('frame_id')
            start_row = post_throw.iloc[0]
            end_row = post_throw.iloc[9]
            dist_start = np.sqrt((start_row['x'] - ball_x)**2 + (start_row['y'] - ball_y)**2)
            dist_end = np.sqrt((end_row['x'] - ball_x)**2 + (end_row['y'] - ball_y)**2)
            actual_closed = dist_start - dist_end
            recovery_tax = 8.0 - actual_closed

        # --- 6. SAVE RESULT ---
        results.append({
            'game_id': gid, 'play_id': pid, 'nfl_id': subject_id,
            'player_name': def_name, 'player_position': def_pos,
            'qb_name': qb_name, 
            'target_name': target_name,
            'decoy_name': decoy_name_str,
            'clv': clv, 'recovery_tax': recovery_tax, 'leak_cause': leak_cause,
            'epa': play_data['expected_points_added'].iloc[0],
            'pass_result': play_data['pass_result'].iloc[0],
            'pass_length': derived_pass_length
        })

        # --- 7. TEMP CACHE (The "Holding Pen") ---
        # We store ANY play with a positive CLV in memory.
        # Later, we will select ONLY the ones that match our Top Players.
        if clv > 0.0:
            clip_start = int(last_frame_pre - 15)
            clip_end = int(last_frame_pre + 15)
            clip = play_data[(play_data['frame_id'] >= clip_start) & (play_data['frame_id'] <= clip_end)].copy()
            clip['highlight_type'] = 'Standard'
            clip['clv_score'] = clv
            clip['target_id'] = target_id 
            clip['nfl_id'] = pd.to_numeric(clip['nfl_id'], errors='coerce').fillna(-1).astype(int).astype(str)
            
            clip_library[(gid, pid)] = clip

    # ==========================================
    # POST-PROCESSING: THE VIP LIST
    # ==========================================
    results_df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(EXPORT_STATS), exist_ok=True)
    
    if not results_df.empty:
        print(f"Calculated metrics for {len(results_df)} plays.")
        results_df.to_csv(EXPORT_STATS, index=False)
        print(f"✅ Saved Stats to {EXPORT_STATS}")

        # --- INTELLIGENT CACHING STRATEGY ---
        print("Selecting VIP Highlights for Cache...")
        final_cache_keys = set()

        # 1. GET THE "BEST REP" FOR TOP 50 PUPPETEERS
        pup_df = results_df[results_df['leak_cause'] == 'Puppeteer']
        qb_bests = pup_df.sort_values('clv', ascending=False).groupby('qb_name').head(1)
        for _, row in qb_bests.iterrows():
            key = (row['game_id'], row['play_id'])
            if key in clip_library:
                clip_library[key]['highlight_type'] = 'QB Best Rep'
                final_cache_keys.add(key)

        # 2. GET THE "BEST REP" FOR TOP 50 DECOYS
        if 'decoy_name' in results_df.columns:
            grav_df = results_df[results_df['leak_cause'] == 'Gravity']
            decoy_bests = grav_df.sort_values('clv', ascending=False).groupby('decoy_name').head(1)
            for _, row in decoy_bests.iterrows():
                key = (row['game_id'], row['play_id'])
                if key in clip_library:
                    clip_library[key]['highlight_type'] = 'Decoy Best Rep'
                    final_cache_keys.add(key)

        # 3. GET THE "WORST REP" FOR TOP 50 VICTIMS
        def_bests = results_df.sort_values('clv', ascending=False).groupby('player_name').head(1)
        for _, row in def_bests.iterrows():
            key = (row['game_id'], row['play_id'])
            if key in clip_library:
                clip_library[key]['highlight_type'] = 'Victim Worst Rep'
                final_cache_keys.add(key)

        # 4. ADD GLOBAL TOP HIGHLIGHTS (Fill the rest)
        sorted_keys = sorted(clip_library.keys(), key=lambda k: clip_library[k]['clv_score'].iloc[0], reverse=True)
        count = 0
        for k in sorted_keys:
            if count >= MAX_GLOBAL_HIGHLIGHTS: break
            if k not in final_cache_keys:
                clip_library[k]['highlight_type'] = 'Global Highlight'
                final_cache_keys.add(k)
                count += 1

        # 5. EXPORT ONLY THE SELECTED CLIPS
        print(f"Exporting {len(final_cache_keys)} unique clips (VIP + Global)...")
        final_clips = [clip_library[k] for k in final_cache_keys]
        
        if final_clips:
            cache_df = pd.concat(final_clips)
            cache_df.to_csv(EXPORT_CACHE, index=False)
            print(f"✅ Saved Guaranteed Highlights to {EXPORT_CACHE}")
        else:
            print("⚠️ No clips met criteria.")

    else:
        print("❌ No results generated.")

if __name__ == '__main__':
    main()