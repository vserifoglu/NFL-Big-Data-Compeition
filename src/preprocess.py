"""
Preprocessing script to create enriched dataset for analysis.

This script:
1. Loads INPUT, OUTPUT, and supplementary data
2. Merges them into a single enriched dataset
3. Adds useful derived columns (ball landing position, etc.)
4. Saves to data/processed/plays_enriched.csv

Run once: python src/preprocess.py --weeks 1-9
Then use: plays_enriched.csv for all analysis
"""

import pandas as pd
import numpy as np
import argparse
import os
from pathlib import Path


def preprocess_data(weeks: range, input_dir: str = "data", output_dir: str = "data/processed"):
    """
    Preprocess and merge all data into a single enriched dataset.
    
    Args:
        weeks: Range of weeks to process
        input_dir: Directory containing raw data
        output_dir: Directory to save preprocessed data
    """
    print("="*60)
    print("NFL Big Data Bowl 2025 - Data Preprocessing")
    print("="*60)
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Load supplementary data (play-level info)
    print("\n1. Loading supplementary data...")
    suppl_path = os.path.join(input_dir, "supplementary_data.csv")
    suppl = pd.read_csv(suppl_path)
    print(f"   ✓ Loaded {len(suppl):,} plays")
    
    # Select relevant supplementary columns
    suppl_cols = [
        'game_id', 'play_id', 'week', 
        'pass_result', 'team_coverage_type', 'team_coverage_man_zone',
        'yards_gained', 'expected_points_added', 
        'pre_snap_home_team_win_probability'
    ]
    suppl = suppl[suppl_cols]
    
    # Load and merge INPUT/OUTPUT data
    print("\n2. Loading and merging INPUT/OUTPUT data...")
    all_plays = []
    
    train_dir = os.path.join(input_dir, "train")
    
    for week in weeks:
        print(f"\n   Week {week}:")
        
        # File paths
        input_path = os.path.join(train_dir, f"input_2023_w{week:02d}.csv")
        output_path = os.path.join(train_dir, f"output_2023_w{week:02d}.csv")
        
        if not os.path.exists(input_path) or not os.path.exists(output_path):
            print(f"      ⚠️ Files not found, skipping...")
            continue
        
        # Load INPUT and OUTPUT
        input_df = pd.read_csv(input_path)
        output_df = pd.read_csv(output_path)
        
        print(f"      INPUT:  {len(input_df):,} rows")
        print(f"      OUTPUT: {len(output_df):,} rows")
        
        # Extract player metadata from INPUT
        player_meta = input_df[[
            'game_id', 'play_id', 'nfl_id',
            'player_side', 'player_role', 'player_name', 'player_position'
        ]].drop_duplicates()
        
        # Extract ball landing position from INPUT (one per play)
        ball_landing = input_df[[
            'game_id', 'play_id', 'ball_land_x', 'ball_land_y'
        ]].drop_duplicates()
        
        # COMBINE INPUT + OUTPUT for complete route tracking
        # INPUT: Pre-pass route (frames before ball throw)
        # OUTPUT: Post-pass route (frames after ball throw to catch)
        
        # Get the last frame of INPUT per play (when ball is thrown)
        input_last_frame = input_df.groupby(['game_id', 'play_id', 'nfl_id'])['frame_id'].max().reset_index()
        input_last_frame.columns = ['game_id', 'play_id', 'nfl_id', 'input_last_frame']
        
        # Add INPUT data with original frames (phase='pre_pass')
        input_positions = input_df[['game_id', 'play_id', 'nfl_id', 'frame_id', 'x', 'y']].copy()
        input_positions['phase'] = 'pre_pass'
        
        # Merge last frame info with OUTPUT
        output_with_offset = output_df.merge(
            input_last_frame,
            on=['game_id', 'play_id', 'nfl_id'],
            how='left'
        )
        
        # Offset OUTPUT frames to continue from INPUT (make continuous timeline)
        # OUTPUT frame 1 becomes (input_last_frame + 1)
        output_with_offset['frame_id'] = output_with_offset['frame_id'] + output_with_offset['input_last_frame']
        output_with_offset['phase'] = 'post_pass'
        
        # Select columns and combine
        output_positions = output_with_offset[['game_id', 'play_id', 'nfl_id', 'frame_id', 'x', 'y', 'phase']].copy()
        
        # Combine INPUT + OUTPUT into complete route
        combined_route = pd.concat([input_positions, output_positions], ignore_index=True)
        
        # Merge with player metadata
        combined_enriched = combined_route.merge(
            player_meta,
            on=['game_id', 'play_id', 'nfl_id'],
            how='left'
        )
        
        # Merge with ball landing position
        combined_enriched = combined_enriched.merge(
            ball_landing,
            on=['game_id', 'play_id'],
            how='left'
        )
        
        # Merge with supplementary data
        combined_enriched = combined_enriched.merge(
            suppl,
            on=['game_id', 'play_id'],
            how='left'
        )
        
        print(f"      ✓ Combined: {len(combined_enriched):,} rows (INPUT + OUTPUT)")
        
        all_plays.append(combined_enriched)
    
    # Combine all weeks
    print("\n3. Combining all weeks...")
    plays_enriched = pd.concat(all_plays, ignore_index=True)
    
    print(f"   ✓ Total rows: {len(plays_enriched):,}")
    print(f"   ✓ Unique plays: {plays_enriched.groupby(['game_id', 'play_id']).ngroups:,}")
    print(f"   ✓ Columns: {len(plays_enriched.columns)}")
    
    # Add derived columns
    print("\n4. Adding derived columns...")
    
    # Completion flag (1 if pass_result == 'C', 0 otherwise)
    plays_enriched['completion'] = (plays_enriched['pass_result'] == 'C').astype(int)
    
    # Count players per play
    player_counts = plays_enriched.groupby(['game_id', 'play_id', 'frame_id', 'player_role']).size().unstack(fill_value=0)
    player_counts = player_counts.reset_index()
    player_counts.columns.name = None
    
    print(f"   ✓ Added completion flag")
    
    # Data quality checks
    print("\n5. Data quality checks...")
    print(f"   Missing player_side: {plays_enriched['player_side'].isna().sum():,} rows")
    print(f"   Missing player_role: {plays_enriched['player_role'].isna().sum():,} rows")
    print(f"   Missing ball_land_x: {plays_enriched['ball_land_x'].isna().sum():,} rows")
    
    # Filter to relevant players only (Targeted Receiver and Defensive Coverage)
    print("\n6. Filtering to contested catch players...")
    contested_players = plays_enriched[
        plays_enriched['player_role'].isin(['Targeted Receiver', 'Defensive Coverage'])
    ].copy()
    
    print(f"   ✓ Filtered: {len(contested_players):,} rows")
    print(f"   ✓ Unique plays: {contested_players.groupby(['game_id', 'play_id']).ngroups:,}")
    
    # Save to CSV
    output_path = os.path.join(output_dir, "plays_enriched.csv")
    contested_players.to_csv(output_path, index=False)
    
    print(f"\n7. ✓ Saved to: {output_path}")
    print(f"   File size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    
    # Summary statistics
    print("\n" + "="*60)
    print("PREPROCESSING COMPLETE")
    print("="*60)
    print("\nDataset summary:")
    print(f"  Total rows: {len(contested_players):,}")
    print(f"  Unique plays: {contested_players.groupby(['game_id', 'play_id']).ngroups:,}")
    print(f"  Weeks included: {sorted(contested_players['week'].unique())}")
    print(f"  Columns: {list(contested_players.columns)}")
    
    print("\nPlayer roles:")
    print(contested_players['player_role'].value_counts())
    
    print("\nPass results:")
    print(contested_players.groupby('pass_result')['play_id'].nunique())
    
    print("\n" + "="*60)
    print("Next step: Use plays_enriched.csv in your analysis pipeline")
    print("="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Preprocess NFL data into enriched dataset')
    
    parser.add_argument(
        '--weeks',
        type=str,
        default='1',
        help='Week range to process (e.g., "1" or "1-9")'
    )
    
    parser.add_argument(
        '--input-dir',
        type=str,
        default='data',
        help='Directory containing raw data files'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/processed',
        help='Directory to save preprocessed data'
    )
    
    args = parser.parse_args()
    
    # Parse week range
    if '-' in args.weeks:
        start, end = map(int, args.weeks.split('-'))
        weeks = range(start, end + 1)
    else:
        weeks = [int(args.weeks)]
    
    preprocess_data(weeks, args.input_dir, args.output_dir)
