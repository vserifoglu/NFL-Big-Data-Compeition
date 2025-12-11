import os
import pandas as pd
from src.schema import AnalysisReportSchema, AggregationScoresSchema, FullPlayAnimationSchema

class DataExporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.report_schema = AnalysisReportSchema
        self.animation_schema = AggregationScoresSchema
        self.full_animation = FullPlayAnimationSchema

    def export_results(self, df_summary: pd.DataFrame, df_frames: pd.DataFrame):
        """
        1. Validates & Saves the Analytical Report.
        2. Validates & Merges Scores for Animation.
        3. Saves the Master Animation File.
        """
        print(f"   -> Output Directory: {self.output_dir}")

        self.report_schema.validate(df_summary)

        summary_path = os.path.join(self.output_dir, 'eraser_analysis_summary.csv')
        df_summary.to_csv(summary_path, index=False)
        print(f"   -> Saved Eraser Analysis Report to {summary_path}")

        # Define the subset of columns to attach to the visualizer
        score_cols = list(self.animation_schema.to_schema().columns.keys())
        flags_to_merge = self.animation_schema.validate(df_summary[score_cols])

        # MERGE: Left join the scores onto the massive physics dataframe
        # This repeats the score for every frame of the play
        df_animation = df_frames.merge(
            flags_to_merge, 
            on=['game_id', 'play_id', 'nfl_id'], 
            how='left'
        )
        
        self.full_animation.validate(df_animation)

        final_path = os.path.join(self.output_dir, 'master_animation_data.csv')
        df_animation.to_csv(final_path, index=False)
        
        print(f"   -> Saved Animation Master File to {final_path}")