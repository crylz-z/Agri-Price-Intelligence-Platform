"""Check schema of each Silver parquet partition."""

import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

bucket = os.getenv("S3_BUCKET_NAME")

con = duckdb.connect(":memory:")
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute(f"SET s3_region='{os.getenv('AWS_DEFAULT_REGION')}';")
con.execute(f"SET s3_access_key_id='{os.getenv('AWS_ACCESS_KEY_ID')}';")
con.execute(f"SET s3_secret_access_key='{os.getenv('AWS_SECRET_ACCESS_KEY')}';")

for day in range(9, 18):
    path = f"s3://{bucket}/silver/year=2026/month=02/day={day:02d}/clean_prices.parquet"
    try:
        df = con.sql(f"SELECT * FROM read_parquet('{path}') LIMIT 1").df()
        print(f"Day {day:02d}: columns={list(df.columns)} | row={df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"Day {day:02d}: ERROR - {e}")

con.close()
