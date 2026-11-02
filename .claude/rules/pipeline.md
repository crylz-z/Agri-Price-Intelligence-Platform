---
paths:
  - "src/etl/**"
  - "src/core/**"
  - "dbt/**"
  - ".github/workflows/**"
---

# Pipeline rules

## Layer contract
- Raw: `s3://$S3_BUCKET_NAME/raw/table=<id>/updated=<YYYYMMDDTHHMMSS>.csv`, one per PSA release, stored as returned (Windows-1252, CRLF, missing values `.` or `..`), never rewritten. `<id>` drops PSA's `.px`; `updated` is PSA's timestamp without separators.
- Mart: `mart/retail_prices_monthly.parquet`, key `(month, geo_code, commodity)`, rebuilt whole by dbt from the latest snapshot per table.
- Order in `pipeline.main`: ingest; if it wrote anything (or `--build`), `dbt build`; a failed build exits 1.

## Ingest (`src/etl/ingest.py`)
- Change detection is `storage.exists`: one HEAD. Never use s3fs `exists()`/`info()` on R2: a miss adds a ListObjects (Class A). Never list R2 in ingest.
- `download` refuses any body that doesn't start with `"Geolocation","Commodity",`, so an error page can't become an immutable snapshot.
- Honest bot: fixed `apip/<version>` User-Agent, sequential, 1 s delay. Cloudflare 403s bare `urllib` but serves `requests` with this UA. Don't add UA rotation, spoofed headers or jitter.

## dbt (`dbt/`)
- Run as `uv run python -m dbt.cli.main <cmd> --project-dir dbt --profiles-dir dbt`; bare `python -m dbt` has no `__main__`.
- R2 access goes through the plugin `src/etl/dbt_storage.py` → `storage.configure_duckdb`; don't put S3 settings in `profiles.yml`.
- `external` models are written **before** their own tests run. Put every blocking test on `stg_`/`int_` (table) models, so a failure skips the mart and R2 keeps the last good one.
- `psa_snapshot_files()` picks the newest 2 snapshots per table with one `glob()` (1 list); staging reads only those files.
- Geo codes come from `seeds/geolocations.csv` (PSGC, from table metadata on 2026-11-02, identical in all 11 tables). PSA's label case differs across tables (`Philippines` vs `PHILIPPINES`): join on `lower()`.
- `lake_root` var overrides `s3://$S3_BUCKET_NAME` for a local build; DuckDB won't create the local `mart/` folder.

## Known limits
- Staging reads 2 snapshots × 11 tables (~25 MB) from R2 on each build, about 20 s.
- DuckDB over s3fs reads Parquet in many small range requests (57 for the 3 MB mart). Code that reads the whole mart should `cat_file` it once, as `src/dashboard/data.py` does.
