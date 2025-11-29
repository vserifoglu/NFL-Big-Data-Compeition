import os
import glob
import pandas as pd
import numpy as np
import re
import gc

# ==========================================
# 1. CONFIGURATION
# ==========================================
INPUT_DIR = 'data/train'
SUPP_FILE = 'data/supplementary_data.csv'
OUTPUT_FILE = 'data/processed/master_zone_tracking.csv'

KEEP_COLS = [
    'game_id', 'play_id', 'nfl_id', 'frame_id', 'phase',
    'x', 'y', 's', 'a', 'dir', 'o',
    'player_name', 'player_position', 'player_role', 'player_side',
    'team_coverage_man_zone', 'pass_result', 'expected_points_added',
    'ball_land_x', 'ball_land_y', 'play_direction'
]

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def standardize_columns(df):
    """Standardizes column names and Enforces ID Types."""
    rename_map = {
        'gameId': 'game_id', 'playId': 'play_id', 'nflId': 'nfl_id',
        'frameId': 'frame_id', 'displayName': 'player_name', 
        'playDirection': 'play_direction', 'position': 'player_position',
        'x': 'x', 'y': 'y', 's': 's', 'a': 'a', 'dir': 'dir', 'o': 'o'
    }
    df = df.rename(columns=rename_map)
    
    # 🔧 FIX 1: TYPE ENFORCEMENT
    # Force nfl_id to be a standard numeric type (Float to handle NaNs)
    # Then fill NaNs with -1 so we can convert to Int safely for deduplication
    if 'nfl_id' in df.columns:
        df['nfl_id'] = pd.to_numeric(df['nfl_id'], errors='coerce').fillna(-1).astype(int)
        
    return df

def normalize_tracking_data(df):
    """Standardizes field coordinates so offense always moves Left-to-Right."""
    if 'play_direction' not in df.columns: return df
    
    mask = df['play_direction'].str.lower() == 'left'
    
    df.loc[mask, 'x'] = 120 - df.loc[mask, 'x']
    df.loc[mask, 'y'] = 53.3 - df.loc[mask, 'y']
    
    if 'dir' in df.columns: 
        df.loc[mask, 'dir'] = (df.loc[mask, 'dir'] + 180) % 360
    if 'o' in df.columns: 
        df.loc[mask, 'o'] = (df.loc[mask, 'o'] + 180) % 360

    # 🔧 FIX 2: Mirror Dimension Fix for Ball Landing
    if 'ball_land_x' in df.columns:
        df.loc[mask, 'ball_land_x'] = 120 - df.loc[mask, 'ball_land_x']
    if 'ball_land_y' in df.columns:
        df.loc[mask, 'ball_land_y'] = 53.3 - df.loc[mask, 'ball_land_y']
        
    return df

def get_valid_plays_lookup():
    print("   > Loading Supplementary Context...")
    try:
        supp_df = pd.read_csv(SUPP_FILE, low_memory=False)
        supp_df = standardize_columns(supp_df)
        
        valid_mask = (
            (supp_df['team_coverage_man_zone'].astype(str).str.contains('Zone', case=False, na=False)) &
            (supp_df['pass_result'].isin(['C', 'I', 'IN']))
        )
        
        valid_df = supp_df[valid_mask].copy()
        valid_keys = set(zip(valid_df.game_id, valid_df.play_id))
        
        context_cols = ['game_id', 'play_id', 'team_coverage_man_zone', 'pass_result', 'expected_points_added']
        return valid_df[context_cols], valid_keys
        
    except FileNotFoundError:
        print(f"❌ Critical Error: {SUPP_FILE} not found.")
        exit()

# ==========================================
# 3. CORE ETL LOGIC
# ==========================================
def process_week_data(week_num, input_path, output_path, valid_keys, context_df):
    print(f"\n   > Processing Week {week_num}...")
    
    # Load Input (Force Low Memory=False to prevent corruption)
    input_df = pd.read_csv(input_path, low_memory=False)
    input_df = standardize_columns(input_df)
    
    input_df['key_tuple'] = list(zip(input_df.game_id, input_df.play_id))
    input_df = input_df[input_df['key_tuple'].isin(valid_keys)].drop(columns=['key_tuple'])
    
    if input_df.empty: return pd.DataFrame()

    # Load Output
    if output_path and os.path.exists(output_path):
        output_df = pd.read_csv(output_path, low_memory=False)
        output_df = standardize_columns(output_df)
        
        output_df['key_tuple'] = list(zip(output_df.game_id, output_df.play_id))
        output_df = output_df[output_df['key_tuple'].isin(valid_keys)].drop(columns=['key_tuple'])
    else:
        output_df = pd.DataFrame()

    # Bridge Metadata
    meta_cols = ['game_id', 'play_id', 'nfl_id', 'player_name', 'player_position', 'player_role', 'player_side', 'play_direction', 'ball_land_x', 'ball_land_y']
    avail_meta_cols = [c for c in meta_cols if c in input_df.columns]
    player_meta = input_df[avail_meta_cols].drop_duplicates(subset=['game_id', 'play_id', 'nfl_id'])
    
    # STITCHING LOGIC
    if not output_df.empty:
        # Calculate Universal Offset (Max frame of the WHOLE play)
        play_offsets = input_df.groupby(['game_id', 'play_id'])['frame_id'].max().reset_index()
        play_offsets.columns = ['game_id', 'play_id', 'offset']
        
        output_df = output_df.merge(player_meta, on=['game_id', 'play_id', 'nfl_id'], how='left')
        output_df = output_df.merge(play_offsets, on=['game_id', 'play_id'], how='left')
        
        output_df['frame_id'] = output_df['frame_id'] + output_df['offset'].fillna(0)
        output_df = output_df.drop(columns=['offset'])
        
        input_df['phase'] = 'pre_throw'
        output_df['phase'] = 'post_throw'
        
        full_week = pd.concat([input_df, output_df], ignore_index=True)
    else:
        input_df['phase'] = 'pre_throw'
        full_week = input_df

    # CLEANUP
    full_week = normalize_tracking_data(full_week)
    full_week = full_week.merge(context_df, on=['game_id', 'play_id'], how='left')
    
    final_cols = [c for c in KEEP_COLS if c in full_week.columns]
    full_week = full_week[final_cols]
    
    # 🔧 FIX 3: STRICT DEDUPLICATION
    # Now that nfl_id is guaranteed to be Int (or -1), this will work perfectly.
    # We keep 'last' to prefer the Output data (Post-Throw) if there is an overlap.
    full_week = full_week.drop_duplicates(subset=['game_id', 'play_id', 'nfl_id', 'frame_id'], keep='last')
    
    full_week = full_week.sort_values(['game_id', 'play_id', 'frame_id'])
    
    print(f"     + Stitched {len(full_week)} rows.")
    return full_week

# ==========================================
# 4. MAIN PIPELINE
# ==========================================
def main():
    print("🚀 STARTING DATA PIPELINE (Type-Safe Mode)")
    
    context_df, valid_keys = get_valid_plays_lookup()
    print(f"   > Identified {len(valid_keys)} valid Zone Coverage plays.")
    
    input_files = sorted(glob.glob(os.path.join(INPUT_DIR, 'input_2023_w*.csv')))
    output_files = glob.glob(os.path.join(INPUT_DIR, 'output_2023_w*.csv'))
    
    output_map = {re.search(r'w(\d{2})', f).group(1): f for f in output_files if re.search(r'w(\d{2})', f)}

    processed_data = []

    for input_f in input_files:
        week_match = re.search(r'w(\d{2})', input_f)
        if not week_match: continue
        
        week_num = week_match.group(1)
        output_f = output_map.get(week_num, None)
        
        week_df = process_week_data(week_num, input_f, output_f, valid_keys, context_df)
        
        if not week_df.empty:
            processed_data.append(week_df)
            
        gc.collect()

    if processed_data:
        print("\n📦 Concatenating Weeks...")
        master_df = pd.concat(processed_data, ignore_index=True)
        
        print(f"📦 Saving to {OUTPUT_FILE}...")
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        master_df.to_csv(OUTPUT_FILE, index=False)
        print("✅ PIPELINE COMPLETE.")
    else:
        print("⚠️ No data processed.")

if __name__ == '__main__':
    main()