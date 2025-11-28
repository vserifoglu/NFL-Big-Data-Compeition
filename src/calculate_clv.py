import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ==========================================
# CONFIGURATION
# ==========================================
MASTER_FILE = 'data/processed/master_zone_tracking.csv'
EXPORT_STATS = 'clv_data_export.csv'
EXPORT_CACHE = 'animation_cache.csv'
MAX_HIGHLIGHTS = 500  # Keep app fast

# ==========================================
# 1. VISUALIZATION LOGIC
# ==========================================
def generate_visuals(results_df):
    print("Generating Charts...")
    sns.set_theme(style="whitegrid")
    
    # Chart 1: Recovery Tax
    plt.figure(figsize=(10, 6))
    if not results_df.empty and 'recovery_tax' in results_df.columns:
        plot_data = results_df.dropna(subset=['recovery_tax'])
        if len(plot_data) > 500: plot_data = plot_data.sample(n=500, random_state=42)
        
        if not plot_data.empty:
            sns.regplot(data=plot_data, x='clv', y='recovery_tax', 
                       scatter_kws={'alpha':0.5, 's':20}, line_kws={'color':'red'})
            plt.title("The Cost: Mental Deception vs Physical Recovery", fontsize=16, fontweight='bold')
            plt.xlabel("Deception (CLV) [yds/s]", fontsize=12)
            plt.ylabel("Recovery Tax (Lost Yards)", fontsize=12)
            plt.tight_layout()
            plt.savefig('recovery_tax_chart.png')

    # Chart 2: Truth Chart
    plt.figure(figsize=(10, 6))
    def bucket_clv(clv):
        if clv > 1.5: return 'High Leak (Fooled)'
        if clv < -0.5: return 'Locked In (Read It)'
        return 'Neutral'
    
    results_df['Leak_Category'] = results_df['clv'].apply(bucket_clv)
    results_df['is_complete'] = (results_df['pass_result'] == 'C').astype(int)
    
    chart_data = results_df.groupby('Leak_Category')['is_complete'].mean().reset_index()
    chart_data['sort'] = chart_data['Leak_Category'].map({'High Leak (Fooled)': 0, 'Neutral': 1, 'Locked In (Read It)': 2})
    chart_data = chart_data.sort_values('sort')
    
    sns.barplot(data=chart_data, x='Leak_Category', y='is_complete', palette=['#ff4b4b', '#d3d3d3', '#4b4bff'])
    plt.title("The Truth Chart: Completion Probability", fontsize=16, fontweight='bold')
    plt.ylim(0, 1.0)
    plt.tight_layout()
    plt.savefig('truth_chart_final.png')

# ==========================================
# 2. SCOUTING REPORTS
# ==========================================
def generate_reports(results_df):
    print("\n--- SCOUTING REPORTS ---")
    if 'qb_name' not in results_df.columns: return

    # Puppeteers (QB Skill)
    print(">>> THE PUPPETEERS (Top QBs) <<<")
    qb_stats = results_df[results_df['leak_cause'] == 'Puppeteer'].groupby('qb_name').agg(
        Score=('clv', 'mean'), Plays=('clv', 'count'), EPA=('epa', 'mean')
    ).reset_index()
    print(qb_stats[qb_stats['Plays'] >= 5].sort_values('Score', ascending=False).head(5))

    # Gravity (WR Skill)
    print("\n>>> THE GRAVITY INDEX (Top Targets) <<<")
    wr_stats = results_df[results_df['leak_cause'] == 'Gravity'].groupby('target_name').agg(
        Score=('clv', 'mean'), Plays=('clv', 'count'), EPA=('epa', 'mean')
    ).reset_index()
    print(wr_stats[wr_stats['Plays'] >= 5].sort_values('Score', ascending=False).head(5))

# ==========================================
# 3. MAIN ANALYSIS LOGIC
# ==========================================
def main():
    if not os.path.exists(MASTER_FILE):
        print(f"ERROR: {MASTER_FILE} not found. Run 'src/preprocess_data.py' first!")
        return

    print("Loading Master Dataset...")
    df = pd.read_csv(MASTER_FILE)
    
    # Buffer for results
    results = []
    highlight_buffer = [] # Store (abs_score, dataframe)

    print("Analyzing Plays...")
    
    # Group by Play (The Preprocessor already filtered for Zone/Pass)
    for (gid, pid), play_data in df.groupby(['game_id', 'play_id']):
        
        # 1. SETUP: Get Ball Destination
        if 'ball_land_x' not in play_data.columns: continue
        ball_x = play_data['ball_land_x'].iloc[0]
        ball_y = play_data['ball_land_y'].iloc[0]
        if pd.isna(ball_x): continue

        # 2. IDENTIFY PHASES
        # Pre-Throw frames are marked by the preprocessor
        pre_throw = play_data[play_data['phase'] == 'pre_throw']
        if pre_throw.empty: continue
        
        # We define the "Trick Window" as the last 5 frames of the pre-throw phase
        last_frame_pre = pre_throw['frame_id'].max()
        window_start = last_frame_pre - 5
        trick_window = pre_throw[pre_throw['frame_id'] >= window_start]
        
        # 3. IDENTIFY SUBJECT (Nearest Defender at start of window)
        start_frame_data = trick_window[trick_window['frame_id'] == window_start]
        defenders = start_frame_data[start_frame_data['player_role'] == 'Defensive Coverage']
        
        if defenders.empty: continue
        
        # Distance calculation
        dists = np.sqrt((defenders['x'] - ball_x)**2 + (defenders['y'] - ball_y)**2)
        subject_idx = dists.idxmin()
        subject_id = defenders.loc[subject_idx, 'nfl_id']
        
        # Capture Names for Reporting
        def_name = defenders.loc[subject_idx, 'player_name']
        def_pos = defenders.loc[subject_idx, 'player_position']
        
        # Identify QB and Target
        qb_row = start_frame_data[start_frame_data['player_role'] == 'Passer']
        qb_name = qb_row.iloc[0]['player_name'] if not qb_row.empty else "Unknown"
        
        target_row = start_frame_data[start_frame_data['player_role'] == 'Targeted Receiver']
        target_name = target_row.iloc[0]['player_name'] if not target_row.empty else "Unknown"
        target_id = target_row.iloc[0]['nfl_id'] if not target_row.empty else -1

        # 4. VISION LOGIC (Puppeteer vs Gravity)
        leak_cause = 'Gravity'
        if not qb_row.empty:
            qb_x, qb_y = qb_row.iloc[0]['x'], qb_row.iloc[0]['y']
            def_x, def_y, def_o = defenders.loc[subject_idx, ['x', 'y', 'o']]
            
            # Geometry: Angle to QB
            vec_deg = np.degrees(np.arctan2(qb_y - def_y, qb_x - def_x)) % 360
            def_o_math = (90 - def_o) % 360
            
            # Difference
            diff = abs(def_o_math - vec_deg)
            vision_error = min(diff, 360 - diff)
            
            if vision_error < 60: leak_cause = 'Puppeteer'

        # 5. CALCULATE CLV (Mental Metric)
        # Filter for just the subject in the window
        subj_window = trick_window[trick_window['nfl_id'] == subject_id].copy()
        if subj_window.empty: continue
        
        # Vector Math
        dir_rad = np.radians(90 - subj_window['dir'])
        vx = subj_window['s'] * np.cos(dir_rad)
        vy = subj_window['s'] * np.sin(dir_rad)
        
        # Unit vector to ball
        dx = ball_x - subj_window['x']
        dy = ball_y - subj_window['y']
        dist = np.sqrt(dx**2 + dy**2) + 1e-6
        
        # Project velocity onto path to ball
        closing_speed = (vx * (dx/dist)) + (vy * (dy/dist))
        
        # CLV is NEGATIVE closing speed (Positive = Leaking Away)
        clv = -1 * closing_speed.mean()

        # 6. CALCULATE RECOVERY TAX (Physical Metric)
        recovery_tax = np.nan
        post_throw = play_data[(play_data['phase'] == 'post_throw') & (play_data['nfl_id'] == subject_id)]
        
        if len(post_throw) >= 10: # Need at least 1.0s of flight
            post_throw = post_throw.sort_values('frame_id')
            start_row = post_throw.iloc[0]
            end_row = post_throw.iloc[9] # 10th frame (approx 1.0s)
            
            dist_start = np.sqrt((start_row['x'] - ball_x)**2 + (start_row['y'] - ball_y)**2)
            dist_end = np.sqrt((end_row['x'] - ball_x)**2 + (end_row['y'] - ball_y)**2)
            
            actual_closed = dist_start - dist_end
            max_possible = 8.0 # Elite defender closes 8 yds/s
            
            recovery_tax = max_possible - actual_closed

        # 7. SAVE STATS
        results.append({
            'game_id': gid, 'play_id': pid, 'nfl_id': subject_id,
            'player_name': def_name, 'player_position': def_pos,
            'qb_name': qb_name, 'target_name': target_name,
            'clv': clv, 'recovery_tax': recovery_tax, 'leak_cause': leak_cause,
            'epa': play_data['expected_points_added'].iloc[0],
            'pass_result': play_data['pass_result'].iloc[0]
        })

        # 8. CACHE HIGHLIGHTS (Smart Buffering)
        if abs(clv) > 2.0:
            # Prepare Animation Data
            # We take a wider window: 1.5s before -> 1.5s after
            clip_start = last_frame_pre - 15
            clip_end = last_frame_pre + 15
            
            # The Preprocessor already stitched frame_id, so we just filter by range!
            clip = play_data[(play_data['frame_id'] >= clip_start) & (play_data['frame_id'] <= clip_end)].copy()
            
            # Tag metadata for the App
            clip['highlight_type'] = 'High Leak' if clv > 0 else 'Good Read'
            clip['clv_score'] = clv
            clip['target_id'] = target_id 
            # Note: ball_land_x/y is already in the data from preprocessor
            
            highlight_buffer.append((abs(clv), clip))

        # Memory Cleanup: Prune buffer if too big
        if len(highlight_buffer) > (MAX_HIGHLIGHTS * 2):
            highlight_buffer.sort(key=lambda x: x[0], reverse=True)
            highlight_buffer = highlight_buffer[:MAX_HIGHLIGHTS]

    # ==========================================
    # FINALIZE & EXPORT
    # ==========================================
    results_df = pd.DataFrame(results)
    
    if not results_df.empty:
        print(f"Analysis Complete. Calculated metrics for {len(results_df)} plays.")
        
        # Save Stats
        results_df.to_csv(EXPORT_STATS, index=False)
        print(f"✅ Saved Stats to {EXPORT_STATS}")
        
        # Save Highlights
        if highlight_buffer:
            highlight_buffer.sort(key=lambda x: x[0], reverse=True)
            final_clips = [x[1] for x in highlight_buffer[:MAX_HIGHLIGHTS]]
            pd.concat(final_clips).to_csv(EXPORT_CACHE, index=False)
            print(f"✅ Saved Top {len(final_clips)} Highlights to {EXPORT_CACHE}")
        
        # Run Reports
        generate_reports(results_df)
        generate_visuals(results_df)
    else:
        print("❌ No results generated.")

if __name__ == '__main__':
    main()