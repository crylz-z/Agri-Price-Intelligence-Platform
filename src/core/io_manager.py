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
    def save_dataframe(
        df: pd.DataFrame,
        filepath: str,
        file_format: str = "parquet",
        mode: str = "overwrite",
    ):
        # PIPELINE LEAK FIX: Hardcode enforcement of data/raw for CSVs or generally
        # The user requested: "Hardcode the base extraction path to explicitly be data/raw/"
        if file_format == "csv" and "data/raw" not in filepath.replace("\\", "/"):
            # Auto-correct the path if it's just in data/
            if filepath.replace("\\", "/").startswith("data/"):
                filepath = filepath.replace("data/", "data/raw/", 1)
            else:
                # Fallback: Just prepend data/raw/ if it looks like a filename
                filepath = os.path.join("data", "raw", os.path.basename(filepath))

        IOManager.ensure_directory(filepath)

        if file_format == "parquet":
            # Parquet doesn't strictly support 'append' mode in simple to_parquet calls without fastparquet/pyarrow handling
            # implementing basic overwrite for now as instructed
            df.to_parquet(filepath, index=False)
        elif file_format == "csv":
            write_mode = "w" if mode == "overwrite" else "a"
            header = (
                True
                if mode == "overwrite" or not IOManager.check_file_exists(filepath)
                else False
            )
            df.to_csv(filepath, mode=write_mode, header=header, index=False)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    @staticmethod
    def load_dataframe(filepath: str, file_format: str = "parquet"):
        if not IOManager.check_file_exists(filepath):
            return pd.DataFrame()  # Return empty if not found

        if file_format == "parquet":
            return pd.read_parquet(filepath)
        elif file_format == "csv":
            return pd.read_csv(filepath)
        else:
            raise ValueError(f"Unsupported format: {file_format}")
