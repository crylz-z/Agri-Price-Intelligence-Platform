"""Object storage settings: Cloudflare R2 (or any S3-compatible store) via s3fs.

Set S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and S3_ENDPOINT_URL,
e.g. https://<account_id>.r2.cloudflarestorage.com
"""

import os

import duckdb
import s3fs
from fsspec import AbstractFileSystem


def endpoint_url() -> str | None:
    return os.getenv("S3_ENDPOINT_URL") or None


def region() -> str:
    # R2 expects the pseudo-region "auto".
    return os.getenv("AWS_DEFAULT_REGION") or (
        "auto" if endpoint_url() else "ap-southeast-2"
    )


def root() -> str:
    return f"s3://{os.environ['S3_BUCKET_NAME']}"


def filesystem() -> s3fs.S3FileSystem:
    # Credentials come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY via botocore.
    return s3fs.S3FileSystem(
        endpoint_url=endpoint_url(), client_kwargs={"region_name": region()}
    )


def exists(fs: AbstractFileSystem, path: str) -> bool:
    """One HEAD (Class B). s3fs's own exists() adds a ListObjects (Class A) on a miss."""
    if not isinstance(fs, s3fs.S3FileSystem):
        return bool(fs.exists(path))
    bucket, key, _ = fs.split_path(path)
    try:
        fs.call_s3("head_object", Bucket=bucket, Key=key)
    except FileNotFoundError:
        return False
    return True


def configure_duckdb(con: duckdb.DuckDBPyConnection) -> None:
    """Let DuckDB read s3:// paths through s3fs instead of the httpfs extension."""
    con.register_filesystem(filesystem())
