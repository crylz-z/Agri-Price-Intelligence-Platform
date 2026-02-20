"""Test the exact patched DataEngine query."""

import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

bucket = os.getenv("S3_BUCKET_NAME")
silver_path = f"s3://{bucket}/silver/year=*/month=*/day=*/*.parquet"

con = duckdb.connect(":memory:")
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute(f"SET s3_region='{os.getenv('AWS_DEFAULT_REGION')}';")
con.execute(f"SET s3_access_key_id='{os.getenv('AWS_ACCESS_KEY_ID')}';")
con.execute(f"SET s3_secret_access_key='{os.getenv('AWS_SECRET_ACCESS_KEY')}';")

target = "2026-02-17"
start = "2026-02-14"

print(f"Testing LKGV query: {start} to {target}")
print(f"Silver path: {silver_path}")
print()

try:
    df = con.sql(f"""
    WITH windowed_data AS (
        SELECT
            region_name,
            market_name,
            category,
            commodity,
            price,
            extract_dt
        FROM read_parquet('{silver_path}', union_by_name=true)
        WHERE CAST(extract_dt AS VARCHAR) NOT LIKE '%<%'
          AND CAST(extract_dt AS VARCHAR) NOT LIKE '%>%'
          AND CAST(extract_dt AS DATE) BETWEEN '{start}' AND '{target}'
    ),
    ranked AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY region_name, market_name, commodity
                ORDER BY extract_dt DESC
            ) as rn
        FROM windowed_data
    )
    SELECT * EXCLUDE (rn)
    FROM ranked
    WHERE rn = 1
    """).df()
    print(f"Result: {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    if not df.empty:
        print(f"\nSample (first 3 rows):")
        print(df.head(3))
    else:
        print("EMPTY - still broken!")
except Exception as e:
    print(f"ERROR: {e}")

con.close()
