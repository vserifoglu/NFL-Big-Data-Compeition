import pandas as pd
import numpy as np
import pytest
import os
import pandera as pa
from src.data_exporter import DataExporter
from src.schema import AnalysisReportSchema, PhysicsSchema

# --- DYNAMIC FACTORY ---
def mock_data_from_schema(schema_model: type[pa.DataFrameModel], n_rows=1, **overrides):
    """
    Introspects a Pandera Schema Model and generates a DataFrame 
    with compliant dummy data for all columns.
    """
    data = {}
    schema_cols = schema_model.to_schema().columns
    
    for col_name, col_props in schema_cols.items():
        # 1. Determine Type
        dtype = str(col_props.dtype)
        
        # 2. Assign Default Dummy Values based on Type
        if "int" in dtype:
            default_val = 1
        elif "float" in dtype:
            default_val = 0.0
        elif "datetime" in dtype:
            default_val = pd.Timestamp("2024-01-01")
        else: # Strings/Objects
            default_val = "dummy_string"
            
        data[col_name] = [default_val] * n_rows
        
    # 3. Apply Manual Overrides
    for col, value in overrides.items():
        if isinstance(value, (list, np.ndarray, pd.Series)):
            if len(value) != n_rows:
                raise ValueError(f"Override length for {col} must match n_rows")
            data[col] = value
        else:
            data[col] = [value] * n_rows
            
    return pd.DataFrame(data)

# --- TESTS ---

def test_exporter_broadcast_merge(tmp_path):
    """
    PRIORITY 1: The Broadcast.
    Verifies that the single summary score (CEOE) appears on EVERY frame.
    """
    output_dir = str(tmp_path)
    
    # 1. Summary: Has 'void_type'
    df_summary = mock_data_from_schema(
        AnalysisReportSchema, 
        n_rows=1,
        nfl_id=100.0,
        ceoe_score=5.0,
        vis_score=2.5,
        void_type='Tight Window' 
    )

    # 2. Frames: MUST NOT HAVE 'void_type' (to avoid merge collision)
    df_frames = mock_data_from_schema(
        PhysicsSchema,
        n_rows=10,
        game_id=1,
        play_id=1,
        nfl_id=100.0,
        frame_id=np.arange(1, 11),
        phase='post_throw' # Required by PhysicsSchema
        # REMOVED: void_type='Tight Window'
    )
    
    exporter = DataExporter(output_dir)
    exporter.export_results(df_summary, df_frames)
    
    # Validation
    result_path = os.path.join(output_dir, 'master_animation_data.csv')
    df_result = pd.read_csv(result_path)
    
    # Logic Check
    assert len(df_result) == 10
    assert (df_result['ceoe_score'] == 5.0).all()
    # Ensure the merge brought over void_type correctly
    assert (df_result['void_type'] == 'Tight Window').all()


def test_exporter_missing_entities(tmp_path):
    """
    PRIORITY 2: The Ghost Entity (Left Join Check).
    """
    output_dir = str(tmp_path)
    
    # Summary
    df_summary = mock_data_from_schema(
        AnalysisReportSchema, n_rows=1, nfl_id=100.0,
        void_type='High Void'
    )
    
    # Frames: Player + Ball
    p_frames = mock_data_from_schema(
        PhysicsSchema, n_rows=1, nfl_id=100.0, phase='post_throw'
    )
    
    b_frames = mock_data_from_schema(
        PhysicsSchema, n_rows=1, nfl_id=np.nan, phase='post_throw'
    )
    
    df_frames = pd.concat([p_frames, b_frames], ignore_index=True)
    
    exporter = DataExporter(output_dir)
    exporter.export_results(df_summary, df_frames)
    
    result_path = os.path.join(output_dir, 'master_animation_data.csv')
    df_result = pd.read_csv(result_path)
    
    # The Ball should exist with NaN scores
    ball_row = df_result[df_result['nfl_id'].isna()]
    assert len(ball_row) == 1
    assert pd.isna(ball_row.iloc[0]['ceoe_score'])


def test_exporter_io_creation(tmp_path):
    """
    PRIORITY 3: File Creation.
    """
    output_dir = str(tmp_path)
    
    df_summary = mock_data_from_schema(
        AnalysisReportSchema, n_rows=1, 
        void_type='Neutral'
    )
    
    df_frames = mock_data_from_schema(
        PhysicsSchema, n_rows=1, 
        phase='post_throw'
    )
    
    exporter = DataExporter(output_dir)
    exporter.export_results(df_summary, df_frames)
    
    assert os.path.exists(os.path.join(output_dir, 'eraser_analysis_summary.csv'))
    assert os.path.exists(os.path.join(output_dir, 'master_animation_data.csv'))