"""
Data loading utilities for NFL Big Data Bowl 2025.

This module provides functions to load preprocessed data for the contested catch analysis.
"""

import pandas as pd
import numpy as np
import os
from typing import Tuple, List, Optional


def load_preprocessed_data(data_path: str = "data/processed/plays_enriched.csv") -> pd.DataFrame:
    """
    Load the preprocessed enriched dataset.
    
    Args:
        data_path: Path to the preprocessed CSV file
        
    Returns:
        DataFrame with all enriched play data
    """
    print(f"Loading preprocessed data from {data_path}...")
    df = pd.read_csv(data_path)
    print(f"✓ Loaded {len(df):,} rows, {df.groupby(['game_id', 'play_id']).ngroups:,} unique plays")
    return df


def get_play_data(game_id: int, play_id: int, df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract data for a specific play.
    
    Args:
        game_id: Game identifier
        play_id: Play identifier
        df: Preprocessed enriched dataframe
        
    Returns:
        DataFrame for the specific play
    """
    play_data = df[
        (df['game_id'] == game_id) & 
        (df['play_id'] == play_id)
    ].copy()
    
    return play_data


def get_receiver_and_defenders(play_data: pd.DataFrame) -> Tuple[int, List[int]]:
    """
    Get the targeted receiver and defensive coverage players for a play.
    
    Args:
        play_data: Play-specific data
        
    Returns:
        Tuple of (receiver_id, defender_ids)
    """
    # Get targeted receiver (should be unique)
    receiver = play_data[play_data['player_role'] == 'Targeted Receiver']['nfl_id'].unique()
    if len(receiver) == 0:
        raise ValueError("No targeted receiver found")
    receiver_id = receiver[0]
    
    # Get defensive coverage players
    defenders = play_data[play_data['player_role'] == 'Defensive Coverage']['nfl_id'].unique()
    defender_ids = list(defenders)
    
    return receiver_id, defender_ids


def get_ball_landing_position(play_data: pd.DataFrame) -> Tuple[float, float]:
    """
    Get the ball landing position from play data.
    
    Args:
        play_data: Play-specific data
        
    Returns:
        Tuple of (ball_land_x, ball_land_y)
    """
    # Ball landing position should be the same for all rows in the play
    ball_land_x = play_data['ball_land_x'].iloc[0]
    ball_land_y = play_data['ball_land_y'].iloc[0]
    
    return ball_land_x, ball_land_y


def get_unique_plays(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get unique play identifiers and metadata.
    
    Args:
        df: Preprocessed enriched dataframe
        
    Returns:
        DataFrame with one row per play
    """
    play_cols = [
        'game_id', 'play_id', 'week', 'pass_result', 
        'team_coverage_type', 'team_coverage_man_zone',
        'yards_gained', 'expected_points_added',
        'pre_snap_home_team_win_probability', 'completion',
        'ball_land_x', 'ball_land_y'
    ]
    
    plays = df[play_cols].drop_duplicates().reset_index(drop=True)
    return plays

import pandas as pd
import os
from typing import Dict, Optional, Tuple


def load_week_data(
    week: int,
    data_dir: str = "data"
) -> Dict[str, pd.DataFrame]:
    """
    Load INPUT, OUTPUT, and supplementary data for a specific week.
    
    Args:
        week: Week number (1-18)
        data_dir: Base directory containing data files (default: "data")
        
    Returns:
        Dictionary with 'input', 'output_enriched', 'supplementary' DataFrames
    """
    train_dir = os.path.join(data_dir, "train")
    suppl_path = os.path.join(data_dir, "supplementary_data.csv")
    
    # File paths
    input_path = os.path.join(train_dir, f"input_2023_w{week:02d}.csv")
    output_path = os.path.join(train_dir, f"output_2023_w{week:02d}.csv")
    
    # Load data
    input_df = pd.read_csv(input_path)
    output_df = pd.read_csv(output_path)
    
    # Enrich OUTPUT with player metadata from INPUT
    output_enriched = enrich_output_data(output_df, input_df)
    
    # Load supplementary data (only once, contains all weeks)
    if os.path.exists(suppl_path):
        suppl_df = pd.read_csv(suppl_path)
    else:
        suppl_df = None
    
    return {
        'input': input_df,
        'output_enriched': output_enriched,
        'supplementary': suppl_df,
        'week': week
    }


def enrich_output_data(output_df: pd.DataFrame, input_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich OUTPUT data with player metadata from INPUT.
    
    OUTPUT only has positions (x, y). INPUT has player_side, player_role, etc.
    This merge is essential for identifying receivers vs defenders.
    
    Args:
        output_df: Raw OUTPUT data (6 columns: game_id, play_id, nfl_id, frame_id, x, y)
        input_df: INPUT data with player metadata (23 columns)
        
    Returns:
        Enriched OUTPUT DataFrame with player_side and player_role columns
    """
    # Extract player metadata from INPUT
    player_meta = input_df[[
        'game_id', 'play_id', 'nfl_id', 
        'player_side', 'player_role'
    ]].drop_duplicates()
    
    # Merge with OUTPUT
    output_enriched = output_df.merge(
        player_meta, 
        on=['game_id', 'play_id', 'nfl_id'], 
        how='left'
    )
    
    return output_enriched


def load_multiple_weeks(
    weeks: range,
    data_dir: str = "data"
) -> Dict[str, pd.DataFrame]:
    """
    Load and combine data from multiple weeks.
    
    Args:
        weeks: Range of weeks to load (e.g., range(1, 10) for weeks 1-9)
        data_dir: Base directory containing data files (default: "data")
        
    Returns:
        Dictionary with combined 'input', 'output_enriched', 'supplementary' DataFrames
    """
    all_input = []
    all_output = []
    suppl_df = None
    
    for week in weeks:
        print(f"Loading Week {week}...")
        try:
            week_data = load_week_data(week, data_dir)
            all_input.append(week_data['input'])
            all_output.append(week_data['output_enriched'])
            
            # Supplementary data is same for all weeks
            if suppl_df is None and week_data['supplementary'] is not None:
                suppl_df = week_data['supplementary']
                
        except FileNotFoundError as e:
            print(f"  ⚠️ Week {week} not found, skipping...")
            continue
    
    if len(all_input) == 0:
        raise FileNotFoundError(
            f"No data files found in '{data_dir}' directory"
        )
    
    # Combine all weeks
    combined_input = pd.concat(all_input, ignore_index=True)
    combined_output = pd.concat(all_output, ignore_index=True)
    
    print(f"\n✓ Total data loaded:")
    print(f"  INPUT: {len(combined_input):,} rows")
    print(f"  OUTPUT: {len(combined_output):,} rows")
    print(f"  Unique plays: {combined_output.groupby(['game_id', 'play_id']).ngroups:,}")
    
    return {
        'input': combined_input,
        'output_enriched': combined_output,
        'supplementary': suppl_df
    }


def get_play_data(
    game_id: int,
    play_id: int,
    output_enriched: pd.DataFrame,
    input_df: Optional[pd.DataFrame] = None
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """
    Extract data for a specific play.
    
    Args:
        game_id: Game identifier
        play_id: Play identifier
        output_enriched: Enriched OUTPUT data
        input_df: INPUT data (optional, for ball landing position)
        
    Returns:
        Tuple of (play_output_data, play_input_data)
    """
    play_output = output_enriched[
        (output_enriched['game_id'] == game_id) & 
        (output_enriched['play_id'] == play_id)
    ].copy()
    
    play_input = None
    if input_df is not None:
        play_input = input_df[
            (input_df['game_id'] == game_id) & 
            (input_df['play_id'] == play_id)
        ].copy()
    
    return play_output, play_input
