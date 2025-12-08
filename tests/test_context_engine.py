import pandas as pd
import numpy as np
from src.context_engine import ContextEngine

def make_context_input_df(num_rows=1, **kwargs):
    """
    Creates a dummy DataFrame.
    accepts **kwargs to override any default column value.
    """
    data = {
        'game_id': [1] * num_rows,
        'play_id': [1] * num_rows,
        'frame_id': np.arange(1, num_rows + 1),

        'nfl_id': np.arange(100, 100 + num_rows).astype(float), 
        'player_role': ['Defensive Coverage'] * num_rows,
        'x': [0.0] * num_rows,
        'y': [0.0] * num_rows,
        'phase': ['pre_throw'] * num_rows,
        'week': [1] * num_rows,

        's_derived': [0.0] * num_rows,
        'a_derived': [0.0] * num_rows
    }
    
    # Override defaults
    for key, value in kwargs.items():
        if isinstance(value, (list, np.ndarray, pd.Series)):
            if len(value) != num_rows:
                raise ValueError(f"Length of {key} ({len(value)}) must match num_rows ({num_rows})")
            data[key] = value
        else:
            data[key] = [value] * num_rows
            
    return pd.DataFrame(data)


def test_context_engine_reduction_logic():
    """
    CRITICAL: Validates that the engine reduces the dataset to EXACTLY 
    one row per play (The Nearest Defender).
    """
    # Setup: 1 Target, 3 Defenders for the SAME play
    # Target
    target = make_context_input_df(1, nfl_id=999.0, player_role='Targeted Receiver', x=0, y=0)
    
    # Defender A (1 yard away)
    def_a = make_context_input_df(1, nfl_id=100.0, x=1, y=0)
    # Defender B (10 yards away)
    def_b = make_context_input_df(1, nfl_id=101.0, x=10, y=0)
    # Defender C (20 yards away)
    def_c = make_context_input_df(1, nfl_id=102.0, x=20, y=0)
    
    df = pd.concat([target, def_a, def_b, def_c])
    
    # Execute
    engine = ContextEngine()
    result = engine.calculate_void_context(df)
    
    # Assert
    assert len(result) == 1, f"Reduction Failed! Expected 1 row, got {len(result)}"
    
    row = result.iloc[0]
    assert row['nearest_def_nfl_id'] == 100.0, "Did not pick the nearest neighbor"
    assert row['dist_at_throw'] == 1.0


def test_context_engine_snapshot_timing():
    """
    Validates that distance is calculated at the THROW (Last Frame).
    """
    # Setup: 1 Target, 1 Defender, moving over time
    
    # Frame 1 (Snap): Distance = 1.0
    t1 = make_context_input_df(1, frame_id=1, nfl_id=999.0, player_role='Targeted Receiver', x=0)
    d1 = make_context_input_df(1, frame_id=1, nfl_id=100.0, player_role='Defensive Coverage', x=1)
    
    # Frame 10 (Throw): Distance = 10.0
    t10 = make_context_input_df(1, frame_id=10, nfl_id=999.0, player_role='Targeted Receiver', x=0)
    d10 = make_context_input_df(1, frame_id=10, nfl_id=100.0, player_role='Defensive Coverage', x=10)
    
    df = pd.concat([t1, d1, t10, d10])

    engine = ContextEngine()
    result = engine.calculate_void_context(df)

    row = result.iloc[0]
    # Use np.isclose for float safety
    assert np.isclose(row['dist_at_throw'], 10.0), "Engine did not use the last frame (Throw)"
    assert row['void_type'] == 'High Void'


def test_context_engine_thresholds():
    """
    Validates the classification buckets.
    """
    # Play 1: Tight (< 2.0)
    p1_t = make_context_input_df(1, play_id=1, nfl_id=901.0, player_role='Targeted Receiver', x=0)
    p1_d = make_context_input_df(1, play_id=1, nfl_id=101.0, player_role='Defensive Coverage', x=1.5)
    
    # Play 2: High Void (> 5.0)
    p2_t = make_context_input_df(1, play_id=2, nfl_id=902.0, player_role='Targeted Receiver', x=0)
    p2_d = make_context_input_df(1, play_id=2, nfl_id=102.0, player_role='Defensive Coverage', x=6.0)
    
    # Play 3: Neutral (2.0 - 5.0)
    p3_t = make_context_input_df(1, play_id=3, nfl_id=903.0, player_role='Targeted Receiver', x=0)
    p3_d = make_context_input_df(1, play_id=3, nfl_id=103.0, player_role='Defensive Coverage', x=3.0)
    
    df = pd.concat([p1_t, p1_d, p2_t, p2_d, p3_t, p3_d])
    
    engine = ContextEngine()
    result = engine.calculate_void_context(df).sort_values('play_id')
    
    assert result.iloc[0]['void_type'] == 'Tight Window'
    assert result.iloc[1]['void_type'] == 'High Void'
    assert result.iloc[2]['void_type'] == 'Neutral'