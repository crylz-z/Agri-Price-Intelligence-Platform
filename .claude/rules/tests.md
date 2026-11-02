---
paths:
  - "tests/**"
---

# Test rules

- No test touches the network or S3; pipeline tests use a local fsspec filesystem.
- `tests/fixtures/*.html` are live responses saved 2026-10-30 (NCR, category 8), kept byte for byte (pre-commit skips them). Refresh them if the site layout changes.
- For real S3 behaviour, run moto ephemerally with botocore pinned to the lock version (newer botocore breaks aiobotocore): `uv run --with "moto[server]" --with "botocore==<uv.lock version>" moto_server -p 5055` and point `S3_ENDPOINT_URL` at it.
