---
paths:
  - "tests/**"
---

# Test rules

- Run with `uv run python -m pytest`. No test touches the network or S3.
- `tests/fixtures/*.html` are live responses saved 2026-10-30 (NCR, category 8). Refresh them if the site layout changes.
- `test_scraper.py`: parsing, failure isolation and the circuit breaker, via a fake session. `test_pipeline.py`: raw/clean layout, dedup, rerun, checks, on a local fsspec filesystem. `test_data_engine.py`: dashboard queries against a clean layer built by the pipeline.
- For real S3 behaviour, run moto ephemerally with botocore pinned to the lock version (newer botocore breaks aiobotocore): `uv run --with "moto[server]" --with "botocore==<uv.lock version>" moto_server -p 5055` and point `S3_ENDPOINT_URL` at it.
