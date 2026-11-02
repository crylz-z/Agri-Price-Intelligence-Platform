---
paths:
  - "tests/**"
---

# Test rules

- No test touches the network or S3; pipeline tests use a local fsspec filesystem.
- `tests/fixtures/psa_condiments.csv` is the header and 3 rows (national, NCR, Abra) of a live PSA response saved 2026-11-02, kept byte for byte (CRLF; pre-commit skips it). Refresh it if PSA changes the CSV layout.
- For real S3 behaviour, run moto ephemerally with botocore pinned to the lock version (newer botocore breaks aiobotocore): `uv run --with "moto[server]" --with "botocore==<uv.lock version>" moto_server -p 5055` and point `S3_ENDPOINT_URL` at it.
