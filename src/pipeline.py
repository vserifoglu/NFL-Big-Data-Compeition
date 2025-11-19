"""
Main pipeline for NFL Big Data Bowl 2025 Analysis.

This script:
1. Loads preprocessed data
2. Calculates SQI and BAA metrics for all plays
3. Trains execution gap model
4. Identifies over/under performers
5. Saves results
"""

import pandas as pd
import numpy as np
import argparse
import os
from pathlib import Path

from data_loader import load_preprocessed_data, get_play_data, get_ball_landing_position
from metrics import calculate_sqi, calculate_baa, calculate_res
from models import ExecutionGapModel


def calculate_metrics_for_all_plays(df: pd.DataFrame, max_plays: int = None) -> pd.DataFrame:
    """
    Calculate SQI, BAA, and RES metrics for all plays in the dataset.
    
    Args:
        df: Preprocessed enriched dataframe
        max_plays: Optional limit on number of plays to process (for testing)
        
    Returns:
        DataFrame with one row per play and calculated metrics
    """
    print("\n" + "="*60)
    print("Calculating metrics for all plays...")
    print("="*60)
    
    # Get unique plays
    plays = df[['game_id', 'play_id']].drop_duplicates()
    
    if max_plays:
        plays = plays.head(max_plays)
        print(f"  Testing mode: Processing first {max_plays} plays")
    
    results = []
    failed_plays = 0
    
    for idx, (game_id, play_id) in enumerate(plays.values):
        if (idx + 1) % 500 == 0:
            print(f"  Progress: {idx + 1}/{len(plays)} plays ({100*(idx+1)/len(plays):.1f}%)")
        
        try:
            # Get all play data (INPUT + OUTPUT)
            play_data_all = df[(df['game_id'] == game_id) & (df['play_id'] == play_id)]
            
            # For SQI/BAA: only use post-pass frames (OUTPUT) - faster
            play_data_post = play_data_all[play_data_all['phase'] == 'post_pass']
            
            # For SQI/BAA: only use post-pass frames (OUTPUT) - faster
            play_data_post = play_data_all[play_data_all['phase'] == 'post_pass']
            
            # Get ball landing position
            ball_land_x = play_data_all['ball_land_x'].iloc[0]
            ball_land_y = play_data_all['ball_land_y'].iloc[0]
            
            # Calculate SQI and BAA using post-pass frames only
            sqi = calculate_sqi(play_data_post)
            baa = calculate_baa(play_data_post, ball_land_x, ball_land_y)
            
            # Calculate RES using complete route (pre-pass + post-pass)
            res = calculate_res(play_data_all, ball_land_x, ball_land_y)
            
            # Get play metadata
            play_meta = play_data_all.iloc[0]
            
            results.append({
                'game_id': game_id,
                'play_id': play_id,
                'week': play_meta['week'],
                'pass_result': play_meta['pass_result'],
                'completion': play_meta['completion'],
                'team_coverage_type': play_meta['team_coverage_type'],
                'team_coverage_man_zone': play_meta['team_coverage_man_zone'],
                'yards_gained': play_meta['yards_gained'],
                'expected_points_added': play_meta['expected_points_added'],
                'sqi': sqi,
                'baa': baa,
                'res': res
            })
            
        except Exception as e:
            failed_plays += 1
            # print(f"  Warning: Failed to process play {game_id}-{play_id}: {e}")
            continue
    
    print(f"\n  ✓ Successfully processed: {len(results)} plays")
    print(f"  ✗ Failed: {failed_plays} plays")
    
    return pd.DataFrame(results)


def train_execution_gap_model(metrics_df: pd.DataFrame) -> ExecutionGapModel:
    """
    Train the execution gap model using SQI as predictor.
    
    Args:
        metrics_df: DataFrame with metrics and outcomes
        
    Returns:
        Trained ExecutionGapModel
    """
    print("\n" + "="*60)
    print("Training Execution Gap Model...")
    print("="*60)
    
    # Filter out plays with missing SQI
    train_data = metrics_df.dropna(subset=['sqi', 'completion'])
    
    print(f"  Training samples: {len(train_data)}")
    print(f"  Completions: {train_data['completion'].sum()} ({100*train_data['completion'].mean():.1f}%)")
    
    # Train model
    model = ExecutionGapModel()
    X = train_data[['sqi']].values
    y = train_data['completion'].values
    
    model.fit(X, y)
    
    # Calculate accuracy
    predictions = model.predict_proba(X)
    predicted_class = (predictions >= 0.5).astype(int)
    accuracy = (predicted_class == y).mean()
    
    print(f"  ✓ Model trained")
    print(f"  Training accuracy: {accuracy:.3f}")
    
    return model


def calculate_execution_gaps(metrics_df: pd.DataFrame, model: ExecutionGapModel) -> pd.DataFrame:
    """
    Calculate execution gaps for all plays.
    
    Args:
        metrics_df: DataFrame with metrics
        model: Trained ExecutionGapModel
        
    Returns:
        DataFrame with execution gaps added
    """
    print("\n" + "="*60)
    print("Calculating Execution Gaps...")
    print("="*60)
    
    # Make predictions
    valid_plays = metrics_df.dropna(subset=['sqi'])
    X = valid_plays[['sqi']].values
    
    expected_catch_rate = model.predict_proba(X)
    execution_gap = model.calculate_execution_gap(
        valid_plays['completion'].values,
        expected_catch_rate
    )
    
    # Add to dataframe
    metrics_df.loc[valid_plays.index, 'expected_catch_rate'] = expected_catch_rate
    metrics_df.loc[valid_plays.index, 'execution_gap'] = execution_gap
    
    print(f"  ✓ Calculated execution gaps for {len(valid_plays)} plays")
    print(f"  Mean execution gap: {execution_gap.mean():.3f}")
    print(f"  Std execution gap: {execution_gap.std():.3f}")
    
    return metrics_df


def save_results(metrics_df: pd.DataFrame, output_path: str):
    """
    Save results to CSV.
    
    Args:
        metrics_df: DataFrame with all metrics and execution gaps
        output_path: Path to save results
    """
    print("\n" + "="*60)
    print("Saving Results...")
    print("="*60)
    
    # Create output directory
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    metrics_df.to_csv(output_path, index=False)
    
    print(f"  ✓ Saved to: {output_path}")
    print(f"  Rows: {len(metrics_df)}")
    print(f"  Columns: {list(metrics_df.columns)}")


def print_summary(metrics_df: pd.DataFrame):
    """
    Print summary statistics.
    
    Args:
        metrics_df: DataFrame with all metrics
    """
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    print("\nMetric Distributions:")
    print(f"  SQI:  mean={metrics_df['sqi'].mean():.2f}, std={metrics_df['sqi'].std():.2f}, "
          f"min={metrics_df['sqi'].min():.2f}, max={metrics_df['sqi'].max():.2f}")
    print(f"  BAA:  mean={metrics_df['baa'].mean():.2f}, std={metrics_df['baa'].std():.2f}, "
          f"min={metrics_df['baa'].min():.2f}, max={metrics_df['baa'].max():.2f}")
    print(f"  RES:  mean={metrics_df['res'].mean():.2f}%, std={metrics_df['res'].std():.2f}%, "
          f"min={metrics_df['res'].min():.2f}%, max={metrics_df['res'].max():.2f}%")
    
    # Count invalid RES values
    res_valid = metrics_df['res'].notna().sum()
    res_total = len(metrics_df)
    print(f"       Valid RES calculations: {res_valid}/{res_total} ({100*res_valid/res_total:.1f}%)")
    
    print("\nExecution Gap Distribution:")
    eg_valid = metrics_df['execution_gap'].dropna()
    print(f"  Mean: {eg_valid.mean():.3f}")
    print(f"  Std:  {eg_valid.std():.3f}")
    print(f"  Min:  {eg_valid.min():.3f}")
    print(f"  Max:  {eg_valid.max():.3f}")
    
    print("\nTop 5 Clutch Plays (Biggest Over-Performance):")
    top_clutch = metrics_df.nlargest(5, 'execution_gap')[
        ['game_id', 'play_id', 'week', 'sqi', 'expected_catch_rate', 'completion', 'execution_gap']
    ]
    print(top_clutch.to_string(index=False))
    
    print("\nTop 5 Missed Opportunities (Biggest Under-Performance):")
    top_missed = metrics_df.nsmallest(5, 'execution_gap')[
        ['game_id', 'play_id', 'week', 'sqi', 'expected_catch_rate', 'completion', 'execution_gap']
    ]
    print(top_missed.to_string(index=False))


def main(args):
    """Main pipeline execution."""
    print("="*60)
    print("NFL BIG DATA BOWL 2025 - EXECUTION GAP ANALYSIS")
    print("="*60)
    
    # 1. Load preprocessed data
    df = load_preprocessed_data(args.data_path)
    
    # 2. Calculate metrics for all plays
    metrics_df = calculate_metrics_for_all_plays(df, max_plays=args.max_plays)
    
    # 3. Train execution gap model
    model = train_execution_gap_model(metrics_df)
    
    # 4. Calculate execution gaps
    metrics_df = calculate_execution_gaps(metrics_df, model)
    
    # 5. Save results
    save_results(metrics_df, args.output_path)
    
    # 6. Print summary
    print_summary(metrics_df)
    
    print("\n" + "="*60)
    print("PIPELINE COMPLETE ✓")
    print("="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run NFL contested catch analysis pipeline')
    
    parser.add_argument(
        '--data-path',
        type=str,
        default='data/processed/plays_enriched.csv',
        help='Path to preprocessed enriched data'
    )
    
    parser.add_argument(
        '--output-path',
        type=str,
        default='outputs/results/all_plays_metrics.csv',
        help='Path to save results'
    )
    
    parser.add_argument(
        '--max-plays',
        type=int,
        default=None,
        help='Maximum number of plays to process (for testing). Default: all plays'
    )
    
    args = parser.parse_args()
    main(args)
