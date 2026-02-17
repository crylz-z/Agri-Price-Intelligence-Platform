"""Query S3 Silver to see all available dates."""
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

bucket = os.getenv('S3_BUCKET_NAME')
s3_path = f"s3://{bucket}/silver/year=*/month=*/day=*/*.parquet"

con = duckdb.connect(":memory:")
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute(f"SET s3_region='{os.getenv('AWS_DEFAULT_REGION')}';")
con.execute(f"SET s3_access_key_id='{os.getenv('AWS_ACCESS_KEY_ID')}';")
con.execute(f"SET s3_secret_access_key='{os.getenv('AWS_SECRET_ACCESS_KEY')}';")

print("Querying Silver layer dates...")
query = f"""
SELECT DISTINCT CAST(extract_dt AS DATE) as date, COUNT(*) as records
FROM read_parquet('{s3_path}', hive_partitioning=true)
GROUP BY CAST(extract_dt AS DATE)
ORDER BY date DESC
"""

df = con.sql(query).df()
print(df)
print(f"\nTotal unique dates: {len(df)}")
