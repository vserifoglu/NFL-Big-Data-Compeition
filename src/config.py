from pydantic import BaseModel
from typing import Optional

class DataPipelineConfig(BaseModel):
    DATA_DIR: str = "data/train"
    SUPP_FILE: str = "data/supplementary_data.csv"
    OUTPUT_DIR: str = "data/processed"


class VisPipelineConfig(BaseModel):
    OUTPUT_DIR: str = "static/visuals_test"
    TRACKING_FILE: str = "data/processed/master_animation_data.csv"
    SUMMARY_FILE: str = "data/processed/eraser_analysis_summary.csv"


# Default config instance
data_config = DataPipelineConfig()
vis_config = VisPipelineConfig()
