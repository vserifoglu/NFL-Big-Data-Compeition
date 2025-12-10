import pandas as pd
from schema import BenchMarkingSchema, AnalysisReportSchema


class BenchmarkingEngine:
    """
    benchmarking defender performance using context and physics data.
    Calculates CEOE (Closing Efficiency Over Expectation) for each play/defender.
    """
    def __init__(self):
        self.bench_schema = BenchMarkingSchema
        self.report_schema = AnalysisReportSchema

    def calculate_ceoe(self, df_metrics: pd.DataFrame, 
                       df_context: pd.DataFrame, df_physics: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate CEOE (Closing Efficiency Over Expectation) for defenders.
        CEOE = Player's avg closing speed - Positional/contextual average.
        """
        meta_cols = list(self.bench_schema.to_schema().columns.keys())
        df_meta = self.bench_schema.validate(df_physics[meta_cols])
        df_meta = df_meta.drop_duplicates()

        df_final = df_metrics.merge(df_meta, on=['game_id', 'play_id', 'nfl_id'], how='left')
        df_final = df_final.merge(
            df_context[['game_id', 'play_id', 'void_type', 'dist_at_throw']], 
            on=['game_id', 'play_id'], 
            how='left'
        )

        # Calculate positional/contextual average closing speed
        benchmarks = df_final.groupby(
            ['player_position', 'void_type'])['avg_closing_speed'].transform('mean')

        df_final['ceoe_score'] = df_final['avg_closing_speed'] - benchmarks
        df_final['ceoe_score'] = df_final['ceoe_score'].fillna(0.0)
        
        return self.report_schema.validate(df_final)