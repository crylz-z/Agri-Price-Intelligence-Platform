---
paths:
  - "src/etl/**"
  - "src/core/**"
  - "dbt/**"
  - ".github/workflows/**"
---

# Pipeline rules

## Layer contract
- Raw: `s3://$S3_BUCKET_NAME/raw/table=<id>/updated=<YYYYMMDDTHHMMSS>.csv`, one per PSA release, stored as returned (Windows-1252, CRLF, missing values `.`, `..` or `...`), never rewritten. `<id>` drops PSA's `.px`; `updated` is PSA's timestamp without separators. Retail and farmgate tables share this prefix.
- Marts, rebuilt whole by dbt from the latest snapshot per table: `mart/retail_prices_monthly.parquet` (key `month, geo_code, commodity`), `staple_prices_monthly` (`month, geo_code, staple`), `dish_costs_monthly` (`month, geo_code, dish`), `staple_seasonality` (`staple, calendar_month`), `farmer_share_monthly` (`month, geo_code, staple`).
- Order in `pipeline.main`: ingest; if it wrote anything (or `--build`), `dbt build`; a failed build exits 1.

## Ingest (`src/etl/ingest.py`)
- Change detection is `storage.exists`: one HEAD. Never use s3fs `exists()`/`info()` on R2: a miss adds a ListObjects (Class A). Never list R2 in ingest.
- Two PSA folders: every retail table in `2018NEW`, and only `FARMGATE_TABLES` in `NFG`. `FARMGATE_TABLES` must match `seeds/psa_farmgate_tables.csv`; a pytest checks it.
- `download` accepts only a body that starts with its table's own CSV header (`Table.header`: PSA lays farmgate tables out differently), so an error page can't become an immutable snapshot.
- Honest bot: fixed `ph-food-prices/<version>` User-Agent, sequential, 1 s delay. Cloudflare 403s bare `urllib` but serves `requests` with this UA. Don't add UA rotation, spoofed headers or jitter.

## dbt (`dbt/`)
- Run as `uv run python -m dbt.cli.main <cmd> --project-dir dbt --profiles-dir dbt`; bare `python -m dbt` has no `__main__`.
- R2 access goes through the plugin `src/etl/dbt_storage.py` → `storage.configure_duckdb`; don't put S3 settings in `profiles.yml`.
- `external` models are written **before** their own tests run. Put every blocking test on `stg_`/`int_` (table) models, so a failure skips the mart and R2 keeps the last good one.
- `psa_snapshot_files(farmgate=…)` picks the newest 2 snapshots per table with one `glob()` (1 list); staging reads only those files. Farmgate means listed in `seeds/psa_farmgate_tables.csv`, and every other table is retail, so a new PSA retail table still trips the retail tests. The calling model needs `-- depends_on: {{ ref('psa_farmgate_tables') }}`.
- Retail geo codes come from `seeds/geolocations.csv` (PSGC, from table metadata on 2026-11-02, identical in all 11 retail tables). PSA's label case differs across tables (`Philippines` vs `PHILIPPINES`): join on `lower()`.
- Farmgate quirks, handled in `stg_psa__farmgate_prices` and `int_farmer_share`:
  - Region labels differ from retail and some carry a footnote mark (`1/`): strip it and map through `seeds/farmgate_geolocations.csv`.
  - Province price cells carry footnote marks, so staging drops province rows before the cast.
  - `0.00` means no sales, not a price: the share keeps `price > 0` only.
  - AFN11 names its commodity column `Type`; EFGP0 puts `Commodity` first.
  - Units are PSA's stated unit: pesos per kg for most, per piece for eggs.
- `lake_root` var overrides `s3://$S3_BUCKET_NAME` for a local build; DuckDB won't create the local `mart/` folder.

## Known limits
- Staging reads 2 snapshots × 19 tables (11 retail, about 12 MB a snapshot set; 8 farmgate, about 11 MB) from R2 on each build, about 46 MB. Retail alone took about 20 s; the farmgate share is not yet timed on R2.
- DuckDB over s3fs reads Parquet in many small range requests (57 for the 3 MB mart). Code that reads the whole mart should `cat_file` it once, as `src/dashboard/data.py` does.
