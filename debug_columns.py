import pandas as pd
import glob
import os

files = glob.glob("data/clean/*.parquet")
if files:
    latest = max(files, key=os.path.getctime)
    df = pd.read_parquet(latest)
    print("COLUMNS:", df.columns.tolist())
else:
    print("No files found")
