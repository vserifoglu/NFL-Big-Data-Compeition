import pandas as pd
from src.analysis.story_data_engine import StoryDataEngine

class MockStoryEngine(StoryDataEngine):
    def __init__(self, summary_df):
        self.summary_df = summary_df
        self.frames_path = "dummy.csv"
        self.seed = 42

def test_story_engine_sampling_logic():
    """
    Verifies that _select_candidate picks from the top N, not just index 0.
    """
    # Setup: 10 Candidates. 
    # ID 1 is the "Extreme Outlier" (VIS 100). ID 2-5 are "Good" (VIS 10).
    df = pd.DataFrame({
        'game_id': range(10), 'play_id': range(10), 'nfl_id': range(10),
        'p_dist_at_throw': [15.0] * 10,
        'dist_at_arrival': [0.0] * 10,
        # ID 0 is extreme (100), others are 10, 9, 8...
        'vis_score': [100.0, 10.0, 9.9, 9.8, 9.7, 5.0, 4.0, 3.0, 2.0, 1.0]
    })
    
    engine = MockStoryEngine(df)
    
    # We force the pool to be exactly this DF for testing purposes
    # Logic: Sort Descending -> Top 5 are IDs [0, 1, 2, 3, 4]
    # Random State 42 should pick one of them.
    selected = engine._select_candidate(df, 'vis_score', False, top_n=5)
    
    assert len(selected) == 1
    # Ensure we picked a "Top 5" candidate (VIS >= 9.7)
    assert selected.iloc[0]['vis_score'] >= 9.7
    
    # Ensure the code runs through cast_archetypes
    cast = engine.cast_archetypes()
    assert cast['Eraser'] is not None
    assert cast['Eraser']['vis_score'] >= 9.7

def test_story_engine_empty_input():
    # Setup: Empty DataFrame
    df = pd.DataFrame(columns=[
        'game_id', 'play_id', 'nfl_id', 
        'p_dist_at_throw', 'vis_score', 'dist_at_arrival'
    ])
    
    engine = MockStoryEngine(df)
    cast = engine.cast_archetypes()
    
    assert cast['Eraser'] is None
    assert cast['Lockdown'] is None