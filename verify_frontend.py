import os
import pandas as pd
from datetime import datetime
from src.dashboard.utils.data_engine import DataEngine

print("Testing app.py date selection...")
# Mock app.py
y = datetime.today().strftime("%Y")
m = datetime.today().strftime("%m")
con = DataEngine._get_connection()

bucket = os.getenv("S3_BUCKET_NAME")
fast_silver_path = f"s3://{bucket}/silver/year={y}/month={m}/*/*.parquet"
try:
    query = f"SELECT MAX(extract_dt) as max_date FROM read_parquet('{fast_silver_path}', union_by_name=true) WHERE CAST(extract_dt AS DATE) <= CURRENT_DATE()"
    max_date_df = con.sql(query).df()
    print("max_date_df:", max_date_df)

    latest_date = pd.to_datetime(max_date_df.iloc[0]["max_date"]).date()
    selected_date = latest_date.strftime("%Y-%m-%d")
except Exception as e:
    print("app.py failed:", e)
    selected_date = "2026-02-18"

print(f"selected_date is: {selected_date}")

print("Fetching snapshot...")
raw_df = DataEngine.get_market_snapshot(selected_date, window_days=3)
print(f"raw_df rows: {len(raw_df)}")

# Region
valid_regions = sorted(raw_df["region_name"].dropna().unique())
print("valid_regions length:", len(valid_regions))
selected_region = (
    "NCR (NATIONAL CAPITAL REGION)"
    if "NCR (NATIONAL CAPITAL REGION)" in valid_regions
    else valid_regions[0]
    if valid_regions
    else ""
)
print("selected_region:", selected_region)

region_df = raw_df[raw_df["region_name"] == selected_region].copy()

# Category
valid_categories = sorted(region_df["category"].dropna().unique().tolist())
if "OTHER COMMODITIES" in [c.upper() for c in valid_categories]:
    actual = next(c for c in valid_categories if c.upper() == "OTHER COMMODITIES")
    valid_categories.remove(actual)
    valid_categories.append(actual)

selected_category = valid_categories[0] if valid_categories else ""
category_df = region_df[region_df["category"] == selected_category].copy()

# Commodity
valid_commodities = sorted(category_df["commodity"].dropna().unique())
selected_commodity = valid_commodities[0] if valid_commodities else ""

print("Fetching historical trends...")
trend_df = DataEngine.get_historical_trends(
    selected_commodity, selected_region, days_back=30, end_date_str=selected_date
)
print(f"trend_df rows: {len(trend_df)}")

print("Test complete!")
