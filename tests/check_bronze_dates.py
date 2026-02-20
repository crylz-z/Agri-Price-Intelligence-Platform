"""Check Bronze layer data range in S3."""

import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

bucket = os.getenv("S3_BUCKET_NAME")
bronze_path = f"s3://{bucket}/bronze/year=*/month=*/day=*/*.csv"

con = duckdb.connect(":memory:")
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute(f"SET s3_region='{os.getenv('AWS_DEFAULT_REGION')}';")
con.execute(f"SET s3_access_key_id='{os.getenv('AWS_ACCESS_KEY_ID')}';")
con.execute(f"SET s3_secret_access_key='{os.getenv('AWS_SECRET_ACCESS_KEY')}';")

print("Querying Bronze layer dates...")
query = f"""
SELECT DISTINCT CAST(extract_dt AS DATE) as date, COUNT(*) as records
FROM read_csv_auto('{bronze_path}', header=True, union_by_name=true)
GROUP BY CAST(extract_dt AS DATE)
ORDER BY date ASC
"""

df = con.sql(query).df()
print(df)
print(f"\nTotal unique dates in Bronze: {len(df)}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
