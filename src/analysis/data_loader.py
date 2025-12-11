import pandas as pd
import numpy as np

class DataLoader:
    def __init__(self, summary_path, frames_path):
        self.summary_path = summary_path
        self.frames_path = frames_path
        self.summary_df = None
        self.frames_df = None

    def load_data(self):
        print(f"   [Loader] Loading Summary Data...")
        self.summary_df = pd.read_csv(self.summary_path)
        self.frames_df = pd.read_csv(self.frames_path)
        
        return self.summary_df, self.frames_df