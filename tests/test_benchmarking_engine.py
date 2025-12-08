import pandas as pd
import numpy as np
from src.benchmarking_engine import BenchmarkingEngine

def make_benchmark_inputs(num_plays=1):
    df_metrics = pd.DataFrame({
        'game_id': [1] * num_plays,
        'play_id': np.arange(1, num_plays + 1),
        'nfl_id': [100.0] * num_plays,
        'avg_closing_speed': [15.0] * num_plays,
        'vis_score': [1.0] * num_plays,       # Float
        'dist_at_arrival': [0.0] * num_plays, # Float
        'distance_closed': [5.0] * num_plays  # Float
    })

    df_context = pd.DataFrame({
        'game_id': [1] * num_plays,
        'play_id': np.arange(1, num_plays + 1),
        'void_type': ['High Void'] * num_plays,
        'dist_at_throw': [10.0] * num_plays,
        'target_nfl_id': [999.0] * num_plays,
        'nearest_def_nfl_id': [100.0] * num_plays
    })

    frames = []
    for p in range(1, num_plays + 1):
        for f in range(1, 6):
            frames.append({
                'game_id': 1,
                'play_id': p,
                'nfl_id': 100.0,
                'frame_id': f,
                'week': 1,
                'player_role': 'Defensive Coverage',
                'player_position': 'CB'
            })
    df_physics = pd.DataFrame(frames)
    
    return df_metrics, df_context, df_physics

def test_benchmarking_deduplication():
    """
    TEST 1: The Duplicate Explosion.
    """
    df_metrics, df_context, df_physics = make_benchmark_inputs(num_plays=1)
    
    engine = BenchmarkingEngine()
    result = engine.calculate_ceoe(df_metrics, df_context, df_physics)
    
    assert len(result) == 1, f"Merge Error! Expected 1 row, got {len(result)}."
    assert result.iloc[0]['player_position'] == 'CB'

def test_benchmarking_positional_grouping():
    """
    TEST 2: Apples to Apples.
    """
    # Metrics
    df_metrics = pd.DataFrame({
        'game_id': [1, 1, 1], 'play_id': [1, 2, 3],
        'nfl_id': [101.0, 102.0, 201.0],
        'avg_closing_speed': [20.0, 10.0, 10.0],
        # FIX: Explicit 0.0 floats to match Schema
        'vis_score': [0.0]*3, 
        'dist_at_arrival': [0.0]*3, 
        'distance_closed': [0.0]*3
    })
    
    # Context (All High Void)
    df_context = pd.DataFrame({
        'game_id': [1]*3, 'play_id': [1, 2, 3],
        'void_type': ['High Void']*3,
        'dist_at_throw': [10.0]*3,
        'target_nfl_id': [999.0]*3, 'nearest_def_nfl_id': [0.0]*3
    })
    
    # Physics (Define Positions)
    df_physics = pd.DataFrame({
        'game_id': [1]*3, 'play_id': [1, 2, 3],
        'nfl_id': [101.0, 102.0, 201.0],
        'player_position': ['CB', 'CB', 'LB'], 
        'week': [1]*3, 'player_role': ['Def']*3
    })
    
    engine = BenchmarkingEngine()
    result = engine.calculate_ceoe(df_metrics, df_context, df_physics)
    
    # Check CB1 (Speed 20 vs CB Avg 15) -> CEOE should be +5.0
    cb1 = result[result['nfl_id'] == 101.0].iloc[0]
    assert np.isclose(cb1['ceoe_score'], 5.0), f"CB Logic Fail. Got {cb1['ceoe_score']}"
    
    # Check LB1 (Speed 10 vs LB Avg 10) -> CEOE should be 0.0
    lb1 = result[result['nfl_id'] == 201.0].iloc[0]
    assert np.isclose(lb1['ceoe_score'], 0.0), f"LB Logic Fail. Got {lb1['ceoe_score']}"

def test_benchmarking_math_sign():
    """
    TEST 3: The Sign Check.
    """
    df_metrics = pd.DataFrame({
        'game_id': [1, 1], 'play_id': [1, 2], 'nfl_id': [100.0, 200.0],
        'avg_closing_speed': [20.0, 10.0], # Avg = 15.0
        # FIX: Explicit 0.0 floats to match Schema
        'vis_score': [0.0]*2, 
        'dist_at_arrival': [0.0]*2, 
        'distance_closed': [0.0]*2
    })
    
    df_context = pd.DataFrame({
        'game_id': [1]*2, 'play_id': [1, 2],
        'void_type': ['Neutral']*2,
        'dist_at_throw': [5.0]*2,
        'target_nfl_id': [999.0]*2, 'nearest_def_nfl_id': [0.0]*2
    })
    
    df_physics = pd.DataFrame({
        'game_id': [1]*2, 'play_id': [1, 2], 'nfl_id': [100.0, 200.0],
        'player_position': ['CB', 'CB'],
        'week': [1]*2, 'player_role': ['Def']*2
    })
    
    engine = BenchmarkingEngine()
    result = engine.calculate_ceoe(df_metrics, df_context, df_physics)
    
    # Player 1 (20.0) vs Avg (15.0) -> +5.0
    p1 = result[result['nfl_id'] == 100.0].iloc[0]
    assert p1['ceoe_score'] > 0, "Better than average should be positive"
    assert np.isclose(p1['ceoe_score'], 5.0)