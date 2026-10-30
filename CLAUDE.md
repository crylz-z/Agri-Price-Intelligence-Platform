# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Python pipeline + dashboard for Philippine retail food prices. `src/etl/pipeline.py` scrapes DA Bantay Presyo (`http://www.bantaypresyo.da.gov.ph`, HTTP only), writes one raw Parquet per run to Cloudflare R2, rebuilds the touched `clean/` partitions with DuckDB (`sql/clean.sql`), and publishes them only if `src/etl/checks.py` passes. A Streamlit dashboard (`src/dashboard/`) reads `clean/`. GitHub Actions (`.github/workflows/daily_run.yml`) runs the quality gate, then the pipeline at 12:00 and 20:30 PHT.

## Quick Start
`make` is not installed; Smart App Control blocks `pytest.exe`, so use `python -m pytest`.
- Install: `uv sync`
- Test: `uv run python -m pytest` · Single: `uv run python -m pytest tests/test_pipeline.py::<name>`
- Lint + types: `uv run ruff format && uv run ruff check . --fix && uv run mypy`
- Pipeline: `uv run python -m src.etl.pipeline` · Dashboard: `uv run streamlit run src/dashboard/app.py`

## Hard Constraints
- **R2 must stay $0/month.** Follow `docs/cloudfare-agent-notes/free-tier-r2.md`: no Infrequent Access, no `ListObjects` or overwrite loops, flag anything that grows storage toward 10 GB or Class A ops toward 1M/month. A run today costs ~4 Class A ops (1 list, 1 raw put, 1-2 clean puts).
- **Storage settings come from `src/core/storage.py` only.** DuckDB reads `s3://` through s3fs (`configure_duckdb`), never the `httpfs` extension, which Smart App Control blocks.
- **Times are Asia/Manila.** Partition dates and "today" use PHT, never UTC or naive local time.
- **The dashboard is frozen** apart from `DataEngine` data access.

## Topic Docs
Path-scoped rules in `.claude/rules/` load automatically when you touch matching files:
- `pipeline.md` — data contract, layer paths, scraper behaviour
- `dashboard.md` — dashboard data layer and caching
- `tests.md` — what the tests cover and how to test against S3
