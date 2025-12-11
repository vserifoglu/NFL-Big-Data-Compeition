import os
from datetime import datetime
import gc
from src.config import DataPipelineConfig, data_config
from src.load_data import DataLoader
from src.data_preprocessor import DataPreProcessor
from src.physics_engine import PhysicsEngine
from src.context_engine import ContextEngine
from src.eraser_engine import EraserEngine
from src.benchmarking_engine import BenchmarkingEngine
from src.data_exporter import DataExporter

def run_full_pipeline(DATA_DIR=None, SUPP_FILE=None, OUTPUT_DIR=None):
    start_time = datetime.now()
    print("hello")
    # Use provided arguments, else fall back to config.py values
    cfg = DataPipelineConfig(
        DATA_DIR=DATA_DIR or data_config.DATA_DIR,
        SUPP_FILE=SUPP_FILE or data_config.SUPP_FILE,
        OUTPUT_DIR=OUTPUT_DIR or data_config.OUTPUT_DIR
    )

    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    # 1. LOAD
    print(f"[1/7] Initializing Data Loader ({datetime.now().strftime('%H:%M:%S')})...")
    loader = DataLoader(cfg.DATA_DIR, cfg.SUPP_FILE)
    raw_supp = loader.load_supplementary()
    raw_tracking = loader.stream_weeks()

    # 2. PREPROCESS
    print("[2/7] Preprocessing & Stitching frames...")
    processor = DataPreProcessor()
    df_clean = processor.run(data_stream=raw_tracking, raw_context_df=raw_supp)

    # 3. PHYSICS
    print("[3/7] Running Physics Engine (Kinematics)...")
    physics_engine = PhysicsEngine()
    df_physics = physics_engine.derive_metrics(df_clean)
    
    del df_clean
    gc.collect() 

    # 4. CONTEXT
    # TODO: Note this is changing the dataframe entirely - df_physics is our animation dataset.
    print("[4/7] Phase A: Calculating Void Context (S_throw)...")
    context_engine = ContextEngine()
    df_context = context_engine.calculate_void_context(df_physics)
    
    # Debugging
    print(f"   -> Identified Voids for {df_context.shape[0]} plays.")

    # 5. ERASER
    print("[5/7] Phase B: Calculating Eraser Metrics (VIS)...")
    eraser_engine = EraserEngine()
    df_metrics = eraser_engine.calculate_eraser(df_physics, df_context)

    # 6. BENCHMARKING
    print("[6/7] Phase C: Benchmarking (CEOE)...")
    benchmarker = BenchmarkingEngine()
    df_final = benchmarker.calculate_ceoe(
        df_metrics=df_metrics, 
        df_context=df_context, 
        df_physics=df_physics
    )

    # 7. EXPORT
    print("[7/7] Phase D: Exporting Results...")
    exporter = DataExporter(cfg.OUTPUT_DIR)
    exporter.export_results(
        df_summary=df_final, 
        df_frames=df_physics
    )
    
    duration = datetime.now() - start_time
    print(f"PIPELINE FINISHED in {duration}")

if __name__ == "__main__":
    run_full_pipeline()