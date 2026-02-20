import boto3
import os
from dotenv import load_dotenv

load_dotenv()


def cleanup_s3():
    bucket = os.getenv("S3_BUCKET_NAME")
    region = os.getenv("AWS_REGION", "ap-southeast-2")
    s3 = boto3.resource("s3", region_name=region)
    bucket_obj = s3.Bucket(bucket)

    # Prefixes to delete
    prefixes_to_delete = [
        "bronze/dlt/",
        "bronze/connectivity_test/",
        "bronze/dlt_dry_run/",
    ]

    print(f"Cleaning bucket: {bucket}")

    for prefix in prefixes_to_delete:
        print(f"Scanning prefix: {prefix}")
        objects_to_delete = []
        for obj in bucket_obj.objects.filter(Prefix=prefix):
            objects_to_delete.append({"Key": obj.key})

        if objects_to_delete:
            print(f"Deleting {len(objects_to_delete)} objects in {prefix}...")
            chunk_size = 1000
            for i in range(0, len(objects_to_delete), chunk_size):
                chunk = objects_to_delete[i : i + chunk_size]
                bucket_obj.delete_objects(Delete={"Objects": chunk})
                print(f"Deleted batch {i//chunk_size + 1}")
        else:
            print(f"No objects found in {prefix}")

    print("Cleanup complete. 'bronze/year=2026/' was preserved.")


if __name__ == "__main__":
    cleanup_s3()
