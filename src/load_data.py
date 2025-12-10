import os
import glob
import re
import pandas as pd
from typing import Generator, Tuple
from schema import RawTrackingSchema, OutputTrackingSchema, RawSuppSchema


class DataLoader:
    def __init__(self, data_dir: str, supp_file: str):
        """
        Scans the directory for files but DOES NOT load them yet.
        """
        self.data_dir = data_dir
        self.supp_file = supp_file

        self.input_files = sorted(glob.glob(os.path.join(self.data_dir, 'input_*.csv')))
        self.output_files = glob.glob(os.path.join(self.data_dir, 'output_*.csv'))
        
        self.output_map = {}
        for f in self.output_files:
            match = re.search(r'w(\d{2})', f)
            if not match:
                continue
            self.output_map[match.group(1)] = f

    def load_supplementary(self) -> pd.DataFrame:
        """
        Loads the single Supplementary file.
        """
        if not os.path.exists(self.supp_file):
            raise FileNotFoundError(f"Missing Supp File: {self.supp_file}")
            
        df = pd.read_csv(self.supp_file, low_memory=False)
            
        return RawSuppSchema.validate(df)

    def stream_weeks(self) -> Generator[Tuple[str, pd.DataFrame, pd.DataFrame], None, None]:
        """
        The Lazy Loader.
        Yields: (week_num, input_df, output_df)
        """

        for input_path in self.input_files:

            # Extract Week Number
            match = re.search(r'w(\d{2})', input_path)
            
            if not match: continue
            week_num = match.group(1)
            
            output_path = self.output_map.get(week_num)

            print(f"Streaming Week {week_num}...")
            
            # Load from Disk
            input_raw = pd.read_csv(input_path, low_memory=False)
            output_raw = pd.read_csv(output_path, low_memory=False)
            
            input_raw['nfl_id'] = pd.to_numeric(input_raw['nfl_id'], errors='coerce')
            output_raw['nfl_id'] = pd.to_numeric(output_raw['nfl_id'], errors='coerce')

            # VALIDATE
            input_valid = RawTrackingSchema.validate(input_raw)
            output_valid = OutputTrackingSchema.validate(output_raw)
            
            # Yield the clean, validated data to the Orchestrator
            yield week_num, input_valid, output_valid