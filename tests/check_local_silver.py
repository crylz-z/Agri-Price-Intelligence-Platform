import pandas as pd

df = pd.read_parquet("data/clean/year=2026/month=02/day=17/market_prices.parquet")
print("Local Silver columns:", df.columns.tolist())
print(f'Has category: {"category" in df.columns}')
print(f'Has market_name: {"market_name" in df.columns}')
if len(df) > 0:
    print(f'region_name sample: {df["region_name"].iloc[0]}')
    if "category" in df.columns:
        print(f'category sample: {df["category"].iloc[0]}')
print(f"Total rows: {len(df)}")
