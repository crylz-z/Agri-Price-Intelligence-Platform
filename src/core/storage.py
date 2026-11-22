"""Object storage settings: Cloudflare R2 (or any S3-compatible store) via s3fs.

Set S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and S3_ENDPOINT_URL,
e.g. https://<account_id>.r2.cloudflarestorage.com
"""

import os
from datetime import datetime
from typing import cast
from urllib.parse import urlparse

import duckdb
import s3fs
from fsspec import AbstractFileSystem


def endpoint_url() -> str | None:
    url = os.getenv("S3_ENDPOINT_URL") or None
    # Cloudflare shows the S3 API URL with the bucket appended. s3fs would then look
    # for every key under <bucket>/<bucket>/ and fail with NoSuchKey.
    if url and urlparse(url).path.strip("/"):
        raise ValueError("S3_ENDPOINT_URL must not include a path; drop the bucket.")
    return url


def region() -> str:
    # R2 expects the pseudo-region "auto".
    return os.getenv("AWS_DEFAULT_REGION") or (
        "auto" if endpoint_url() else "ap-southeast-2"
    )


def root() -> str:
    return f"s3://{os.environ['S3_BUCKET_NAME']}"


def filesystem() -> s3fs.S3FileSystem:
    # Credentials come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY via botocore.
    # Fail fast and retry: botocore's 60 s timeouts let one stalled read hang the
    # dashboard's "Loading" spinner for minutes. read_timeout is per socket read.
    return s3fs.S3FileSystem(
        endpoint_url=endpoint_url(),
        client_kwargs={"region_name": region()},
        config_kwargs={
            "connect_timeout": 5,
            "read_timeout": 20,
            "retries": {"max_attempts": 3, "mode": "standard"},
        },
    )


def modified(fs: AbstractFileSystem, path: str) -> datetime | None:
    """Last write time (UTC) from one HEAD (Class B); None when missing.

    s3fs's own exists()/info() add a ListObjects (Class A) on a miss.
    """
    if not isinstance(fs, s3fs.S3FileSystem):
        when = fs.modified(path) if fs.exists(path) else None
        return cast(datetime | None, when)
    bucket, key, _ = fs.split_path(path)
    try:
        head = fs.call_s3("head_object", Bucket=bucket, Key=key)
    except FileNotFoundError:
        return None
    return cast(datetime, head["LastModified"])


def configure_duckdb(con: duckdb.DuckDBPyConnection) -> None:
    """Let DuckDB read s3:// paths through s3fs instead of the httpfs extension."""
    con.register_filesystem(filesystem())
