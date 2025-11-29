import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ==========================================
# CONFIGURATION
# ==========================================
MASTER_FILE = 'data/processed/master_zone_tracking.csv'
EXPORT_STATS = 'src/clv_data_export.csv'
EXPORT_CACHE = 'src/animation_cache.csv'
MAX_HIGHLIGHTS = 500 

# ==========================================
# 1. VISUALIZATION LOGIC (Updated with Validation)
# ==========================================
def generate_visuals(results_df):
    print("Generating Charts...")
    sns.set_theme(style="whitegrid")
    
    # --- Chart 1: The "Proof" (EPA Validation) ---
    # This proves that your metric actually correlates with winning.
    plt.figure(figsize=(10, 6))
    if 'qb_name' in results_df.columns:
        # Filter for statistically significant sample size (n >= 30 plays)
        qb_summary = results_df.groupby('qb_name').agg(
            Puppeteer_Score=('clv', 'mean'),
            EPA_Per_Play=('epa', 'mean'),
            Plays=('clv', 'count')
        ).reset_index()
        
        valid_qbs = qb_summary[qb_summary['Plays'] >= 30]
        
        if not valid_qbs.empty:
            p1 = sns.regplot(data=valid_qbs, x='Puppeteer_Score', y='EPA_Per_Play', 
                             scatter_kws={'s': valid_qbs['Plays']}, line_kws={'color':'red'})
            
            # Label the outliers
            for line in range(0, valid_qbs.shape[0]):
                p_row = valid_qbs.iloc[line]
                if p_row['Plays'] > 100 or p_row['Puppeteer_Score'] > 1.2 or p_row['EPA_Per_Play'] > 0.4:
                    p1.text(p_row['Puppeteer_Score']+0.02, p_row['EPA_Per_Play'], 
                            p_row['qb_name'], horizontalalignment='left', size='small', color='black')
            
            plt.title("Validation: Does Deception Lead to Points?", fontsize=16, fontweight='bold')
            plt.xlabel("Puppeteer Score (Avg CLV)", fontsize=12)
            plt.ylabel("EPA per Play", fontsize=12)
            plt.tight_layout()
            plt.savefig('validation_epa.png')

    # --- Chart 2: Recovery Tax ---
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

    # --- Chart 3: Truth Chart ---
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
# 2. SCOUTING REPORTS (FINAL ANALYST VERSION)
# ==========================================
def generate_reports(results_df):
    print("\n--- 🏆 NFL STANDARDIZED SCOUTING REPORTS ---")
    if 'qb_name' not in results_df.columns: return

    # -------------------------------------------------------------------------
    # 1. THE PUPPETEERS: SORT BY TOTAL VOLUME (Not Average)
    # -------------------------------------------------------------------------
    print(">>> THE PUPPETEERS (Ranked by Total Void Created) <<<")
    pup_df = results_df[results_df['leak_cause'] == 'Puppeteer'].copy()
    
    # Calculate Total Impact
    qb_stats = pup_df.groupby('qb_name').agg(
        Avg_Score=('clv', 'mean'), 
        Total_Void_Yards=('clv', 'sum'), # <--- The Key Metric
        Plays=('clv', 'count'), 
        EPA=('epa', 'mean')
    ).reset_index()
    
    # FILTER: Remove tiny sample sizes (e.g., < 20 plays)
    elite_qbs = qb_stats[qb_stats['Plays'] >= 20]
    
    # SORT: By TOTAL sum. This puts Purdy/Mahomes/Allen at the top.
    elite_qbs = elite_qbs.sort_values('Total_Void_Yards', ascending=False)
    
    print(elite_qbs.head(10).to_string(index=False))

    # -------------------------------------------------------------------------
    # 2. THE GRAVITY INDEX: GROUP BY DECOY (Not Target)
    # -------------------------------------------------------------------------
    print("\n>>> THE GRAVITY INDEX (The Zone Breakers) <<<")
    grav_df = results_df[results_df['leak_cause'] == 'Gravity'].copy()
    
    # CHECK: Did we successfully capture 'decoy_name' in the main loop?
    if 'decoy_name' in grav_df.columns:
        # Group by the CREATOR (Decoy), not the Catcher
        wr_stats = grav_df.groupby('decoy_name').agg(
            Avg_Void=('clv', 'mean'), 
            Plays=('clv', 'count'), 
            Total_EPA_Created=('epa', 'sum') # <--- Who generated the most points for teammates?
        ).reset_index()
        
        # Filter for real contributors (Min 5 decoys)
        elite_gravity = wr_stats[wr_stats['Plays'] >= 5]
        
        # Sort by Total Value
        elite_gravity = elite_gravity.sort_values('Total_EPA_Created', ascending=False)
        print(elite_gravity.head(10).to_string(index=False))
        
    else:
        print("⚠️ 'decoy_name' column missing! Grouping by Target (Beneficiary) instead:")
        # Fallback if you haven't re-run the main analysis yet
        wr_stats = grav_df.groupby('target_name').agg(
            Avg_Void=('clv', 'mean'), 
            Plays=('clv', 'count')
        ).reset_index()
        print(wr_stats[wr_stats['Plays'] >= 10].sort_values('Avg_Void', ascending=False).head(10))

    # -------------------------------------------------------------------------
    # 3. THE VICTIMS
    # -------------------------------------------------------------------------
    print("\n>>> THE VICTIMS (Most Targeted in Voids) <<<")
    def_stats = results_df.groupby(['player_name', 'player_position']).agg(
        Bait_Score=('clv', 'mean'), 
        Total_Void_Allowed=('clv', 'sum'),
        Plays=('clv', 'count')
    ).reset_index()
    
    # Filter for starters
    victims = def_stats[def_stats['Plays'] >= 20].sort_values('Total_Void_Allowed', ascending=False)
    print(victims.head(10).to_string(index=False))
    
# ==========================================
# 3. MAIN ANALYSIS LOGIC
# ==========================================
def main():
    if not os.path.exists(MASTER_FILE):
        print(f"ERROR: {MASTER_FILE} not found.")
        return

    print("Loading Master Dataset...")
    df = pd.read_csv(MASTER_FILE, low_memory=False)
    
    results = []
    highlight_buffer = [] 
    best_highlights = {}

    print("Analyzing Plays...")
    
    for (gid, pid), play_data in df.groupby(['game_id', 'play_id']):
        
        # 1. Get Ball Destination
        if 'ball_land_x' not in play_data.columns: continue
        ball_x = play_data['ball_land_x'].iloc[0]
        ball_y = play_data['ball_land_y'].iloc[0]
        if pd.isna(ball_x): continue

        # 2. IDENTIFY PHASES
        pre_throw = play_data[play_data['phase'] == 'pre_throw']
        if pre_throw.empty: continue
        
        last_frame_pre = pre_throw['frame_id'].max()
        window_start = last_frame_pre - 10
        trick_window = pre_throw[pre_throw['frame_id'] >= window_start]
        
        if trick_window.empty: continue

        # 3. PREPARE FRAME DATA
        start_frame_data = trick_window[trick_window['frame_id'] == window_start]
        
        # 4. IDENTIFY QB & FILTER GARBAGE TIME
        qb_row = start_frame_data[start_frame_data['player_role'] == 'Passer']
        
        if qb_row.empty: continue 
            
        qb_x = qb_row.iloc[0]['x']
        qb_y = qb_row.iloc[0]['y']
        qb_name = qb_row.iloc[0]['player_name']
        
        derived_pass_length = ball_x - qb_x
        
        # FILTER: Only analyze passes > 8 yards downfield (Removes Screens/Checkdowns)
        if derived_pass_length < 8.0:
            continue 

        # 5. IDENTIFY VICTIM
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

        # ... inside main() loop ...

        # 6. VISION & CAUSALITY LOGIC
        leak_cause = 'Unforced Error' 
        decoy_name_str = None # <--- NEW VARIABLE
        
        def_x, def_y, def_o = defenders.loc[subject_idx, ['x', 'y', 'o']]
        
        # A. Check "Puppeteer"
        vec_qb_deg = np.degrees(np.arctan2(qb_y - def_y, qb_x - def_x)) % 360
        def_o_math = (90 - def_o) % 360
        diff_qb = abs(def_o_math - vec_qb_deg)
        vision_error_qb = min(diff_qb, 360 - diff_qb)
        
        if vision_error_qb < 60: 
            leak_cause = 'Puppeteer'

        # B. Check "Gravity" (The Decoy Tracker)
        else:
            qb_id = qb_row.iloc[0]['nfl_id']
            # Only track SKILL POSITION decoys (No linemen)
            potential_decoys = start_frame_data[
                (start_frame_data['player_position'].isin(['WR', 'TE', 'RB', 'FB'])) & 
                (start_frame_data['nfl_id'] != target_id) & 
                (start_frame_data['nfl_id'] != qb_id)
            ]
            
            min_dist = float('inf')
            max_speed = 0
            best_decoy_row = None # <--- Tracker
            
            for _, decoy in potential_decoys.iterrows():
                d_dist = np.sqrt((decoy['x'] - def_x)**2 + (decoy['y'] - def_y)**2)
                if d_dist < min_dist:
                    min_dist = d_dist
                    max_speed = decoy['s']
                    best_decoy_row = decoy # Save the player row
            
            # CRITERIA:
            # 1. Proximity < 10 yards
            # 2. Speed > 3.0 (Must be running a route, no standing still!)
            # 3. Decoy cannot be an RB (If you want to filter out checkdown gravity)
            if min_dist < 10.0 and max_speed > 3.0:
                leak_cause = 'Gravity'
                if best_decoy_row is not None:
                    decoy_name_str = best_decoy_row['player_name'] # <--- SAVE NAME

        # 7. CALCULATE CLV
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

        # 8. RECOVERY TAX
        recovery_tax = np.nan
        post_throw = play_data[(play_data['phase'] == 'post_throw') & (play_data['nfl_id'] == subject_id)]
        
        if len(post_throw) >= 10:
            post_throw = post_throw.sort_values('frame_id')
            start_row = post_throw.iloc[0]
            end_row = post_throw.iloc[9]
            
            dist_start = np.sqrt((start_row['x'] - ball_x)**2 + (start_row['y'] - ball_y)**2)
            dist_end = np.sqrt((end_row['x'] - ball_x)**2 + (end_row['y'] - ball_y)**2)
            
            actual_closed = dist_start - dist_end
            max_possible = 8.0 
            recovery_tax = max_possible - actual_closed

        # 9. SAVE STATS
        results.append({
            'game_id': gid, 'play_id': pid, 'nfl_id': subject_id,
            'player_name': def_name, 'player_position': def_pos,
            'qb_name': qb_name, 
            'target_name': target_name,
            'decoy_name': decoy_name_str, # <--- NEW FIELD
            'clv': clv, 'recovery_tax': recovery_tax, 'leak_cause': leak_cause,
            'epa': play_data['expected_points_added'].iloc[0],
            'pass_result': play_data['pass_result'].iloc[0],
            'pass_length': derived_pass_length
        })

        # 10. CACHE HIGHLIGHTS (With ID Stringification Fix)
        if clv > 6.0:
            current_best_score = best_highlights.get((gid, pid), (0, None))[0]
            
            if clv > current_best_score:
                clip_start = int(last_frame_pre - 15)
                clip_end = int(last_frame_pre + 15)
                clip = play_data[(play_data['frame_id'] >= clip_start) & (play_data['frame_id'] <= clip_end)].copy()
                clip['highlight_type'] = 'High Leak'
                clip['clv_score'] = clv
                clip['target_id'] = target_id 
                # CRITICAL FIX for Animation: Force IDs to clean strings here at the source
                clip['nfl_id'] = pd.to_numeric(clip['nfl_id'], errors='coerce').fillna(-1).astype(int).astype(str)
                best_highlights[(gid, pid)] = (clv, clip)

    results_df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(EXPORT_STATS), exist_ok=True)

    highlight_buffer = list(best_highlights.values())
    
    if not results_df.empty:
        print(f"Analysis Complete. Calculated metrics for {len(results_df)} plays.")
        results_df.to_csv(EXPORT_STATS, index=False)
        print(f"✅ Saved Stats to {EXPORT_STATS}")
        
        if highlight_buffer:
            highlight_buffer.sort(key=lambda x: x[0], reverse=True)
            top_clips = [x[1] for x in highlight_buffer[:MAX_HIGHLIGHTS]]
            if top_clips:
                print("Concatenating clips...")
                cache_df = pd.concat(top_clips)
                cache_df.to_csv(EXPORT_CACHE, index=False)
                print(f"✅ Saved Top {len(top_clips)} Highlights to {EXPORT_CACHE}")
        
        generate_reports(results_df)
        generate_visuals(results_df)
    else:
        print("❌ No results generated.")

if __name__ == '__main__':
    main()