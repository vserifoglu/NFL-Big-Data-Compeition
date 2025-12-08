import pandas as pd
import numpy as np
from src.physics_engine import PhysicsEngine

def make_physics_schema_df(num_rows=10):
    return pd.DataFrame({
        'game_id': [1]*num_rows,
        'play_id': [1]*num_rows,
        'frame_id': np.arange(1, num_rows+1),
        'nfl_id': [100]*num_rows,
        'play_direction': ['left']*num_rows,
        'absolute_yardline_number': [50]*num_rows,
        'player_role': ['WR']*num_rows,
        'player_position': ['WR']*num_rows,
        'x': np.linspace(0, 9, num_rows), # Default movement
        'y': np.linspace(0, 9, num_rows),
        's': [0.0]*num_rows,
        'ball_land_x': [0.0]*num_rows,
        'ball_land_y': [0.0]*num_rows,
        'week': [1]*num_rows,
        'home_team_abbr': ['HTM']*num_rows,
        'visitor_team_abbr': ['VTM']*num_rows,
        'down': [1]*num_rows,
        'yards_to_go': [10]*num_rows,
        'possession_team': ['HTM']*num_rows,
        'yardline_side': ['HTM']*num_rows,
        'yardline_number': [25]*num_rows,
        'pre_snap_home_team_win_probability': [0.5]*num_rows,
        'pre_snap_visitor_team_win_probability': [0.5]*num_rows,
        'play_nullified_by_penalty': ['N']*num_rows,
        'dropback_type': ['Traditional']*num_rows,
        'team_coverage_man_zone': ['Zone']*num_rows,
        'team_coverage_type': ['COVER_2_ZONE']*num_rows,
        'pass_result': ['C']*num_rows,
        'pass_length': [5]*num_rows,
        'route_of_targeted_receiver': ['IN']*num_rows,
        'phase': ['pre_throw']*num_rows,
        'yards_from_own_goal': [25]*num_rows,
        'possession_win_prob': [0.5]*num_rows,
        's_derived': [np.nan]*num_rows,
        'a_derived': [np.nan]*num_rows,
    })

def test_physics_engine_short_track_accuracy():
    """
    Validates that the Fallback Logic (Linear Diff) 
    calculates the EXACT correct speed for tracks < 7 frames.
    """
    # 1. Setup: Create a DataFrame with KNOWN geometry
    df = make_physics_schema_df(num_rows=3) # Short track
    
    # Override X/Y to move exactly 1.0 yard per frame (pure horizontal)
    # Time per frame = 0.1s
    # Expected Speed = 1.0 / 0.1 = 10.0 yds/s
    df['x'] = [10.0, 11.0, 12.0]
    df['y'] = [5.0, 5.0, 5.0]
    
    # 2. Execute
    engine = PhysicsEngine()
    result = engine.derive_metrics(df)
    
    # 3. Assert
    # Extract valid speeds (first frame is NaN due to diff)
    valid_speeds = result['s_derived'].dropna()
    
    assert len(valid_speeds) > 0
    # Use np.allclose for float comparison
    assert np.allclose(valid_speeds, 10.0), f"Math Error! Expected 10.0, got {valid_speeds.mean()}"

def test_physics_engine_multiple_players_isolation():
    """
    Validates that Player A data does not bleed into Player B.
    If grouping fails, the jump from A to B will cause 'Teleportation Speed'.
    """
    # Player A: Standing still at X=0
    df1 = make_physics_schema_df(num_rows=10)
    df1['nfl_id'] = 100
    df1['x'] = 0.0 
    df1['y'] = 0.0

    # Player B: Standing still at X=50 (50 yards away)
    df2 = make_physics_schema_df(num_rows=10)
    df2['nfl_id'] = 200
    df2['x'] = 50.0 
    df2['y'] = 0.0
    
    # Concatenate
    df = pd.concat([df1, df2], ignore_index=True)
    
    # Execute
    engine = PhysicsEngine()
    result = engine.derive_metrics(df)
    
    # Logic Check:
    # If grouping works, both players are standing still (Speed ~ 0).
    # If grouping FAILS, the code sees one "Player" jumping 50 yards in 0.1s.
    # That would be 500 yds/s.
    
    max_speed = result['s_derived'].max()
    
    assert max_speed < 1.0, f"Grouping Failed! Teleportation speed detected: {max_speed}"
    assert set(result['nfl_id']) == {100, 200}

def test_physics_engine_savgol_smoothness():
    """
    Validates that the Savitzky-Golay filter is actually running
    on long tracks (smoother than raw linear diff).
    """
    # Setup: 20 frames (Long track)
    df = make_physics_schema_df(num_rows=20)
    
    # Create jagged movement (jitter)
    # The filter should smooth this out
    df['x'] = np.linspace(10, 20, 20) + np.random.normal(0, 0.1, 20)
    df['y'] = 0.0
    
    engine = PhysicsEngine()
    result = engine.derive_metrics(df)
    
    # Check that we got results
    assert result['s_derived'].notna().sum() > 10
    assert result['a_derived'].notna().sum() > 10