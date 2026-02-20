"""Test simplified Silver layer transformation to S3."""

import duckdb
import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

bucket = os.getenv("S3_BUCKET_NAME")
region = os.getenv("AWS_DEFAULT_REGION")
access_key = os.getenv("AWS_ACCESS_KEY_ID")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

# Use today's date
target_date = "2026-02-17"
dt = datetime.strptime(target_date, "%Y-%m-%d")
year, month, day = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")

bronze_path = f"s3://{bucket}/bronze/year={year}/month={month}/day={day}/*.csv"
silver_path = (
    f"s3://{bucket}/silver/year={year}/month={month}/day={day}/clean_prices.parquet"
)

print(f"Testing simplified Silver transformation for {target_date}\n")

# Setup DuckDB
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute(f"SET s3_region='{region}';")
con.execute(f"SET s3_access_key_id='{access_key}';")
con.execute(f"SET s3_secret_access_key='{secret_key}';")

# Register region map
REGION_MAP = {
    "010000000": "REGION I (ILOCOS REGION)",
    "020000000": "REGION II (CAGAYAN VALLEY)",
    "030000000": "REGION III (CENTRAL LUZON)",
    "040000000": "REGION IV-A (CALABARZON)",
    "050000000": "REGION V (BICOL REGION)",
    "060000000": "REGION VI (WESTERN VISAYAS)",
    "070000000": "REGION VII (CENTRAL VISAYAS)",
    "080000000": "REGION VIII (EASTERN VISAYAS)",
    "090000000": "REGION IX (ZAMBOANGA PENINSULA)",
    "100000000": "REGION X (NORTHERN MINDANAO)",
    "110000000": "REGION XI (DAVAO REGION)",
    "120000000": "REGION XII (SOCCSKSARGEN)",
    "130000000": "REGION XIII (Caraga)",
    "140000000": "CAR (CORDILLERA ADMINISTRATIVE REGION)",
    "150000000": "NCR (NATIONAL CAPITAL REGION)",
    "160000000": "REGION IV-B (MIMAROPA)",
    "170000000": "BARMM (Bangsamoro Autonomous Region of Muslim Mindanao)",
}

region_df = pd.DataFrame(list(REGION_MAP.items()), columns=["region_id", "region_name"])
con.register("region_map", region_df)

print("Step 1: Testing query without COPY (dry run)...")
silver_query = f"""
SELECT
    extract_dt,
    COALESCE(m.region_name, CAST(r.region_id AS VARCHAR)) as region_name,
    r.market_name,
    r.category,
    r.commodity,
    CAST(r.price AS DOUBLE) as price
FROM read_csv_auto('{bronze_path}', header=True, union_by_name=true) r
LEFT JOIN region_map m ON CAST(r.region_id AS VARCHAR) = m.region_id
LIMIT 10
"""

try:
    df = con.sql(silver_query).df()
    print(f"✅ Query works: {len(df)} sample rows\n")
    print(df.head())
except Exception as e:
    print(f"❌ Query failed: {e}\n")
    exit(1)

print("\n\nStep 2: Writing to S3 with COPY...")
full_silver_query = f"""
SELECT
    extract_dt,
    COALESCE(m.region_name, CAST(r.region_id AS VARCHAR)) as region_name,
    r.market_name,
    r.category,
    r.commodity,
    CAST(r.price AS DOUBLE) as price
FROM read_csv_auto('{bronze_path}', header=True, union_by_name=true) r
LEFT JOIN region_map m ON CAST(r.region_id AS VARCHAR) = m.region_id
"""

try:
    con.execute(
        f"COPY ({full_silver_query}) TO '{silver_path}' (FORMAT PARQUET, OVERWRITE_OR_IGNORE true)"
    )
    print(f"✅ Successfully wrote Silver layer to S3\n")
    print(f"Path: {silver_path}")
except Exception as e:
    print(f"❌ S3 write failed: {e}\n")
    exit(1)

print("\nStep 3: Verifying written data...")
verify_df = con.sql(f"SELECT * FROM read_parquet('{silver_path}') LIMIT 5").df()
print(f"✅ Verified: {len(verify_df)} sample rows")
print(f"Columns: {verify_df.columns.tolist()}")

con.close()

print("\n" + "=" * 50)
print("✅ SIMPLIFIED SILVER TRANSFORMATION SUCCEEDED")
print("=" * 50)
