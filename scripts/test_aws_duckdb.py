import duckdb
import os
from dotenv import load_dotenv
import sys

# Color codes for visibility
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def test_connection():
    load_dotenv()

    bucket = os.getenv("S3_BUCKET_NAME")
    key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    print(f"Testing connectivity to S3 Bucket: {bucket}")

    if not all([bucket, key_id, secret]):
        print(f"{RED}[FAILURE] Missing Environment Variables. Check .env{RESET}")
        return

    try:
        con = duckdb.connect(database=":memory:")

        # Modern DuckDB Secret Management
        secret_query = f"""
        CREATE SECRET secret1 (
            TYPE S3,
            KEY_ID '{key_id}',
            SECRET '{secret}',
            REGION '{region}'
        );
        """
        con.execute(secret_query)

        # Test Query
        test_query = f"SELECT * FROM 's3://{bucket}/bronze/*/*/*/*.csv' LIMIT 1"
        print(f"Executing: {test_query}")

        result = con.execute(test_query).fetchall()

        print(f"{GREEN}[SUCCESS] Connection Active!{RESET}")
        print(f"Sample Data: {result}")

    except Exception as e:
        print(f"{RED}[FAILURE] Connection Refused{RESET}")
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
