import os
import pandas as pd
from . import config

class IOManager:
    @staticmethod
    def check_file_exists(filepath):
        return os.path.exists(filepath)

    @staticmethod
    def ensure_directory(filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    @staticmethod
    def save_dataframe(df: pd.DataFrame, filepath: str, file_format: str = 'parquet', mode: str = 'overwrite'):
        IOManager.ensure_directory(filepath)
        
        if file_format == 'parquet':
            # Parquet doesn't strictly support 'append' mode in simple to_parquet calls without fastparquet/pyarrow handling
            # implementing basic overwrite for now as instructed
            df.to_parquet(filepath, index=False)
        elif file_format == 'csv':
            write_mode = 'w' if mode == 'overwrite' else 'a'
            header = True if mode == 'overwrite' or not IOManager.check_file_exists(filepath) else False
            df.to_csv(filepath, mode=write_mode, header=header, index=False)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    @staticmethod
    def load_dataframe(filepath: str, file_format: str = 'parquet'):
        if not IOManager.check_file_exists(filepath):
            return pd.DataFrame() # Return empty if not found

        if file_format == 'parquet':
            return pd.read_parquet(filepath)
        elif file_format == 'csv':
            return pd.read_csv(filepath)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    @staticmethod
    def append_metric_row(filepath: str, row_dict: dict):
        """
        Appends a single row of metrics to a CSV file.
        Handles creating the file with headers if it doesn't exist.
        """
        IOManager.ensure_directory(filepath)
        df = pd.DataFrame([row_dict])
        
        header = not IOManager.check_file_exists(filepath)
        df.to_csv(filepath, mode='a', header=header, index=False)
