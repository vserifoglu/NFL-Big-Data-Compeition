import os
import glob
import pandas as pd
import numpy as np
import re

# ==========================================
# CONFIGURATION
# ==========================================
INPUT_DIR = 'data/train'
SUPP_FILE = 'data/supplementary_data.csv'
OUTPUT_FILE = 'data/processed/master_zone_tracking.csv'

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def standardize_columns(df):
    """Converts raw tracking columns to standardized snake_case."""
    rename_map = {
        'gameId': 'game_id', 'playId': 'play_id', 'nflId': 'nfl_id',
        'frameId': 'frame_id', 'displayName': 'player_name', 
        'playDirection': 'play_direction', 'position': 'player_position',
        'x': 'x', 'y': 'y', 's': 's', 'dir': 'dir', 'o': 'o'
    }
    # Only rename columns that exist
    return df.rename(columns=rename_map)

def normalize_direction(df):
    """Standardizes field coordinates to always play Left-to-Right."""
    if 'play_direction' not in df.columns: return df
    
    mask = df['play_direction'].str.lower() == 'left'
    # Flip Coordinates
    df.loc[mask, 'x'] = 120 - df.loc[mask, 'x']
    df.loc[mask, 'y'] = 53.3 - df.loc[mask, 'y']
    # Flip Angles
    if 'dir' in df.columns: df.loc[mask, 'dir'] = (df.loc[mask, 'dir'] + 180) % 360
    if 'o' in df.columns: df.loc[mask, 'o'] = (df.loc[mask, 'o'] + 180) % 360
    
    return df

# ==========================================
# MAIN PIPELINE
# ==========================================
def main():
    print("🚀 STARTING DATA PREPROCESSING PIPELINE")
    
    # 1. LOAD CONTEXT (The Filter)
    print("   > Loading Supplementary Data...")
    supp_df = pd.read_csv(SUPP_FILE, low_memory=False)
    
    # Standardize Supp Data IDs
    supp_df['game_id'] = supp_df['game_id'].astype(int)
    supp_df['play_id'] = supp_df['play_id'].astype(int)
    
    # FILTER: Only keep Zone Coverage & Valid Pass Plays
    # This reduces data size massively before we even touch tracking data
    valid_plays = supp_df[
        (supp_df['team_coverage_man_zone'].astype(str).str.contains('Zone', case=False, na=False)) &
        (supp_df['pass_result'].isin(['C', 'I', 'IN']))
    ][['game_id', 'play_id', 'team_coverage_man_zone', 'pass_result', 'expected_points_added', 'possession_team']]
    
    print(f"   > Filtered Context: {len(valid_plays)} valid Zone plays identified.")
    
    # Create a set for fast lookup
    valid_keys = set(zip(valid_plays.game_id, valid_plays.play_id))

    # 2. LOCATE FILES
    input_files = sorted(glob.glob(os.path.join(INPUT_DIR, 'input_2023_w*.csv')))
    output_files = glob.glob(os.path.join(INPUT_DIR, 'output_2023_w*.csv'))
    # Map week '01' to output file path
    output_map = {re.search(r'w(\d{2})', f).group(1): f for f in output_files if re.search(r'w(\d{2})', f)}

    # Buffer for processed chunks
    processed_chunks = []
    
    # 3. PROCESS WEEK BY WEEK
    for input_file in input_files:
        week_match = re.search(r'w(\d{2})', input_file)
        if not week_match: continue
        week_num = week_match.group(1)
        
        print(f"\n   > Processing Week {week_num}...")
        
        # Load Raw Data
        input_df = pd.read_csv(input_file)
        input_df = standardize_columns(input_df)
        
        # Filter Input Data immediately (Keep only valid plays)
        # We create a temp key column for filtering
        input_df['key'] = list(zip(input_df.game_id, input_df.play_id))
        input_df = input_df[input_df['key'].isin(valid_keys)].drop(columns=['key'])
        
        if input_df.empty:
            print("     - No valid zone plays in this week.")
            continue

        # Load Output Data (if exists)
        output_df = pd.DataFrame()
        if week_num in output_map:
            output_df = pd.read_csv(output_map[week_num])
            output_df = standardize_columns(output_df)
            # Filter Output Data
            output_df['key'] = list(zip(output_df.game_id, output_df.play_id))
            output_df = output_df[output_df['key'].isin(valid_keys)].drop(columns=['key'])

        # --- PLAY PROCESSING LOOP ---
        # We iterate by play to Stitch Time and Merge Metadata
        
        # 1. Capture Metadata from Input (Name, Position, Role)
        # We need to map nfl_id to player info because Output data lacks it
        meta_cols = ['game_id', 'play_id', 'nfl_id', 'player_name', 'player_position', 'player_role']
        if 'player_side' in input_df.columns: meta_cols.append('player_side')
        
        # Create a metadata lookup table for this week
        meta_df = input_df[meta_cols].drop_duplicates(subset=['game_id', 'play_id', 'nfl_id'])
        
        # 2. Stitching Logic
        # We perform a clever trick: Determine max frame per play in Input, then offset Output
        max_frames = input_df.groupby(['game_id', 'play_id'])['frame_id'].max().reset_index()
        max_frames.columns = ['game_id', 'play_id', 'max_input_frame']
        
        if not output_df.empty:
            # Merge max frame info into output
            output_df = output_df.merge(max_frames, on=['game_id', 'play_id'], how='left')
            # Offset the frames
            output_df['frame_id'] = output_df['frame_id'] + output_df['max_input_frame']
            # Drop helper col
            output_df = output_df.drop(columns=['max_input_frame'])
            
            # Merge Metadata into Output (Restore names/roles)
            output_df = output_df.merge(meta_df, on=['game_id', 'play_id', 'nfl_id'], how='left')
            
            # Label the source
            input_df['phase'] = 'pre_throw'
            output_df['phase'] = 'post_throw'
            
            # Combine
            week_clean = pd.concat([input_df, output_df], ignore_index=True)
        else:
            input_df['phase'] = 'pre_throw'
            week_clean = input_df

        # 3. Normalize Direction & Merge Context
        week_clean = normalize_direction(week_clean)
        week_clean = week_clean.merge(valid_plays, on=['game_id', 'play_id'], how='left')
        
        # 4. Save Memory (Select only needed columns)
        # Add ball_land_x/y if they exist in input
        cols_to_keep = [
            'game_id', 'play_id', 'nfl_id', 'frame_id', 'phase',
            'x', 'y', 's', 'dir', 'o',
            'player_name', 'player_position', 'player_role', 'player_side',
            'team_coverage_man_zone', 'pass_result', 'expected_points_added',
            'ball_land_x', 'ball_land_y'
        ]
        # Keep only columns that actually exist in the dataframe
        cols_to_keep = [c for c in cols_to_keep if c in week_clean.columns]
        
        week_clean = week_clean[cols_to_keep]
        
        processed_chunks.append(week_clean)
        print(f"     + Stitched & Cleaned {len(week_clean)} rows.")

    # 4. EXPORT MASTER FILE
    print("\n📦 Saving Master File...")
    if processed_chunks:
        master_df = pd.concat(processed_chunks, ignore_index=True)
        
        # Sort for cleanliness
        master_df = master_df.sort_values(['game_id', 'play_id', 'frame_id'])
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        master_df.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ SUCCESS: Saved {len(master_df)} rows to {OUTPUT_FILE}")
        print("   You can now delete the raw data folders if you want to save space.")
    else:
        print("❌ FAILURE: No data processed.")

if __name__ == '__main__':
    main()