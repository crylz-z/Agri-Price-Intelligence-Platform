import duckdb
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

def test_read():
    s3_bucket = os.getenv("S3_BUCKET_NAME")
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_DEFAULT_REGION")
    
    con = duckdb.connect()
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    con.execute(f"SET s3_region='{aws_region}';")
    con.execute(f"SET s3_access_key_id='{aws_key}';")
    con.execute(f"SET s3_secret_access_key='{aws_secret}';")
    
    # List one file
    s3 = boto3.client('s3')
    resp = s3.list_objects_v2(Bucket=s3_bucket, Prefix='bronze/year=2026/month=02/day=16/')
    if 'Contents' not in resp:
        print("No files found via Boto3!")
        return
        
    key = resp['Contents'][0]['Key']
    path = f"s3://{s3_bucket}/{key}"
    with open("debug_log.txt", "w", encoding='utf-8') as f:
        # Single file test
        try:
            res = con.sql(f"SELECT * FROM read_csv_auto('{path}') LIMIT 5").fetchall()
            f.write(f"Single file read success: {len(res)} rows\n")
        except Exception as e:
            f.write(f"Single file read failed: {e}\n")
            
        # Glob test
        glob_path = f"s3://{s3_bucket}/bronze/year=2026/month=02/day=16/*.csv"
        f.write(f"Trying glob: {glob_path}\n")
        try:
            res = con.sql(f"SELECT count(*) FROM read_csv_auto('{glob_path}')").fetchall()
            f.write(f"Glob read success: count={res[0][0]}\n")
        except Exception as e:
            f.write(f"Glob read failed: {e}\n")

if __name__ == "__main__":
    test_read()
