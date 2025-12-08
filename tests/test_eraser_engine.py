import pandas as pd
import numpy as np
from src.eraser_engine import EraserEngine

def make_eraser_input(num_rows, nfl_id, role, x_start, x_end, phase='post_throw'):
    """
    Creates linear movement for a player.
    """
    return pd.DataFrame({
        'game_id': [1] * num_rows,
        'play_id': [1] * num_rows,
        'frame_id': np.arange(1, num_rows + 1),
        'nfl_id': [nfl_id] * num_rows,
        'player_role': [role] * num_rows,
        'x': np.linspace(x_start, x_end, num_rows),
        'y': [0] * num_rows, # Simple 1D movement
        'phase': [phase] * num_rows,
        's': [0]*num_rows, 'a': [0]*num_rows, 'dis': [0]*num_rows
    })

def test_eraser_engine_math_signs():
    """
    TEST 1: Eraser vs Busted.
    Validates that Closing = Positive Score, Opening = Negative Score.
    """
    # 1. Target (Stationary at 0)
    target = make_eraser_input(11, 999, 'Targeted Receiver', 0, 0)
    
    # 2. Eraser (Starts at 10, ends at 0). 10 yards / 1.0s = 10yds/s
    eraser = make_eraser_input(11, 100, 'Defensive Coverage', 10, 0)
    
    # 3. Busted (Starts at 2, ends at 12). -10 yards / 1.0s = -10yds/s
    busted = make_eraser_input(11, 200, 'Defensive Coverage', 2, 12)
    
    df = pd.concat([target, eraser, busted])
    
    engine = EraserEngine()
    # Context DF is unused in current script logic, passing empty
    result = engine.calculate_erasure(df, pd.DataFrame())
    
    # Check Eraser
    res_e = result[result['nfl_id'] == 100].iloc[0]
    assert np.isclose(res_e['vis_score'], 10.0), f"Eraser VIS wrong: {res_e['vis_score']}"
    assert res_e['avg_closing_speed'] > 9.0, "Eraser speed should be positive"

    # Check Busted
    res_b = result[result['nfl_id'] == 200].iloc[0]
    assert np.isclose(res_b['vis_score'], -10.0), f"Busted VIS wrong: {res_b['vis_score']}"
    assert res_b['avg_closing_speed'] < -9.0, "Busted speed should be negative"


def test_eraser_engine_phase_filtering():
    """
    TEST 2: Phase Leak.
    Ensures pre_throw data does not pollute the 'Start Distance'.
    """
    # Target stationary
    target_pre = make_eraser_input(5, 999, 'Targeted Receiver', 0, 0, phase='pre_throw')
    target_post = make_eraser_input(5, 999, 'Targeted Receiver', 0, 0, phase='post_throw')
    # Shift post-throw frames to be 6-10
    target_post['frame_id'] += 5
    
    # Defender:
    # Pre-Throw: Far away (50 yards)
    def_pre = make_eraser_input(5, 100, 'Defensive Coverage', 50, 50, phase='pre_throw')
    # Post-Throw: Close (5 yards) and stays there
    def_post = make_eraser_input(5, 100, 'Defensive Coverage', 5, 5, phase='post_throw')
    def_post['frame_id'] += 5
    
    df = pd.concat([target_pre, target_post, def_pre, def_post])
    
    engine = EraserEngine()
    result = engine.calculate_erasure(df, pd.DataFrame())
    
    row = result.iloc[0]
    
    # If filter fails, d_start will be 50, VIS will be 45.
    # If filter works, d_start will be 5, VIS will be 0.
    assert row['vis_score'] == 0.0, f"Phase Leak detected! VIS: {row['vis_score']}"


def test_eraser_engine_ghost_join():
    """
    TEST 3: The Ghost.
    Verifies that calculation stops when the defender disappears (Inner Join).
    """
    # Target exists for frames 1-10 (Stationary at 0)
    target = make_eraser_input(10, 999, 'Targeted Receiver', 0, 0)
    
    # Defender exists for frames 1-5 only.
    # Starts at 10, moves to 5. (Should stop here).
    defender = make_eraser_input(5, 100, 'Defensive Coverage', 10, 5)
    
    df = pd.concat([target, defender])
    
    engine = EraserEngine()
    result = engine.calculate_erasure(df, pd.DataFrame())
    
    row = result.iloc[0]
    
    # d_end should be 5.0 (Frame 5 distance), not NaN or crash
    assert row['dist_at_arrival'] == 5.0
    # VIS should be 5.0 (10 - 5)
    assert row['vis_score'] == 5.0