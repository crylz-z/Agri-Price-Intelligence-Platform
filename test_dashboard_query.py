"""Quick test to verify dashboard data loading."""
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

s3 = os.getenv("S3_BUCKET_NAME")
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute(f"SET s3_region='{os.getenv('AWS_DEFAULT_REGION')}';")
con.execute(f"SET s3_access_key_id='{os.getenv('AWS_ACCESS_KEY_ID')}';")
con.execute(f"SET s3_secret_access_key='{os.getenv('AWS_SECRET_ACCESS_KEY')}';")

silver_path = f"s3://{s3}/silver/year=*/month=*/day=*/*.parquet"

print("Testing dashboard data query...")
df = con.sql(f"""
    SELECT 
        extract_dt,
        region_name,
        market_name,
        category,
        commodity,
        price
    FROM read_parquet('{silver_path}', hive_partitioning=true)
    LIMIT 5
""").df()

print(f"\n✅ Dashboard query works!")
print(f"Columns: {df.columns.tolist()}")
print(f"\nSample data:")
print(df.to_string())
print(f"\nTotal rows: {len(con.sql(f'SELECT COUNT(*) FROM read_parquet(\'{silver_path}\', hive_partitioning=true)').df())}")

# Check for required columns
required = ['extract_dt', 'region_name', 'market_name', 'category', 'commodity', 'price']
missing = [col for col in required if col not in df.columns]
if missing:
    print(f"\n❌ Missing columns: {missing}")
else:
    print(f"\n✅ All required columns present for dashboard")

con.close()
