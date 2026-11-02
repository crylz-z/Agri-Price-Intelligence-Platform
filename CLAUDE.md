# CLAUDE.md

## Project Overview
Python pipeline + dashboard for Philippine monthly retail food prices from PSA OpenSTAT (`https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2M/2018NEW/`). `src/etl/pipeline.py` runs `src/etl/ingest.py`, which stores each new PSA release as an immutable CSV snapshot on Cloudflare R2, then runs `dbt build` (`dbt/`, dbt Core + dbt-duckdb) only if ingest wrote something. dbt tests gate the mart `mart/retail_prices_monthly.parquet`. A 2-page Streamlit dashboard (`src/dashboard/`) reads the mart. GitHub Actions (`.github/workflows/daily_run.yml`) runs the gate (ruff, mypy, pytest, dbt parse) on pushes and PRs, and the pipeline daily at 10:00 PHT and on manual dispatch. Terms: `GLOSSARY.md`; tool choices: `docs/adr.md`.

## Quick Start
`make` is not installed. Run every tool as `uv run python -m <tool>`: it matches CI, the docs and the pre-commit hooks.
- Test: `uv run python -m pytest` · Single: `uv run python -m pytest tests/test_ingest.py::<name>`
- Lint + types: before reporting done, run `uv run python -m pre_commit run --all-files` (ruff, mypy; the same hooks run on `git commit` and in CI).
- dbt: `uv run python -m dbt.cli.main build --project-dir dbt --profiles-dir dbt` (reads and writes R2).
- Query R2 data: `uv run python -m src.etl.query "SELECT ... FROM mart"` (views `raw`, `mart`; read-only).
- Pipeline: `uv run python -m src.etl.pipeline [--build]` · Dashboard: `uv run python -m streamlit run src/dashboard/app.py`

## Hard Constraints
- **R2 must stay $0/month.** Follow `docs/cloudfare-agent-notes/free-tier-r2.md`: no Infrequent Access, no `ListObjects` or overwrite loops, flag anything that grows storage toward 10 GB or Class A ops toward 1M/month. A run with no release costs 11 HEADs (Class B); a release day adds 1 put per new snapshot, 1 list (dbt glob) and 1 mart put.
- **Storage settings come from `src/core/storage.py` only.** DuckDB and dbt reach `s3://` through s3fs (`configure_duckdb`, and the dbt plugin `src/etl/dbt_storage.py`), never the `httpfs` extension.
- **Times are Asia/Manila (PHT).** dbt's connection sets `TimeZone`; ruff `DTZ` enforces timezone-aware Python calls.
- **Raw snapshots are immutable.** Never overwrite or delete one without asking.

## Topic Docs
Path-scoped rules in `.claude/rules/` load automatically when you touch matching files:
- `pipeline.md`: layer paths, ingest, dbt gotchas
- `dashboard.md`: dashboard data layer and caching
- `tests.md`: test fixtures and testing against S3
