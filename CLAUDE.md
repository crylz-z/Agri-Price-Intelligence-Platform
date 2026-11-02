# CLAUDE.md

## Project Overview
Python pipeline + dashboard for Philippine retail food prices. `src/etl/pipeline.py` scrapes DA Bantay Presyo (`http://www.bantaypresyo.da.gov.ph`, HTTP only), writes one raw Parquet per run to Cloudflare R2, rebuilds the touched `clean/` partitions with DuckDB (`sql/clean.sql`), and publishes them only if `src/etl/checks.py` passes. A Streamlit dashboard (`src/dashboard/`) reads `clean/`. GitHub Actions (`.github/workflows/daily_run.yml`) runs the full gate (ruff, mypy, pytest) on pushes and PRs, and only the pipeline at 12:00 and 20:30 PHT.

## Quick Start
`make` is not installed; Smart App Control blocks venv `.exe` shims (`pytest.exe`, `pre-commit.exe`, `streamlit.exe`), so run every tool as `uv run python -m <tool>`.
- Test: `uv run python -m pytest` · Single: `uv run python -m pytest tests/test_pipeline.py::<name>`
- Lint + types: before reporting done, run `uv run python -m pre_commit run --all-files` (ruff, mypy; the same hooks run on `git commit` and in CI).
- Query R2 data: `uv run python -m src.etl.query "SELECT ... FROM raw"` (tables `raw`, `clean`; read-only).
- Pipeline: `uv run python -m src.etl.pipeline` · Dashboard: `uv run python -m streamlit run src/dashboard/app.py`

## Hard Constraints
- **R2 must stay $0/month.** Follow `docs/cloudfare-agent-notes/free-tier-r2.md`: no Infrequent Access, no `ListObjects` or overwrite loops, flag anything that grows storage toward 10 GB or Class A ops toward 1M/month. A run costs ~11 Class A ops: 1 list, 1 raw put, and 1 clean put per posting date in the run (9 on 2026-10-30, at most 17).
- **Storage settings come from `src/core/storage.py` only.** DuckDB reads `s3://` through s3fs (`configure_duckdb`), never the `httpfs` extension, which Smart App Control blocks.
- **Times are Asia/Manila (PHT).** Partition dates and "today" follow DA's posting day; ruff `DTZ` enforces timezone-aware calls.
- **The dashboard is frozen** apart from `DataEngine` data access.

## Topic Docs
Path-scoped rules in `.claude/rules/` load automatically when you touch matching files:
- `pipeline.md` — data contract, layer paths, scraper behaviour
- `dashboard.md` — dashboard data layer and caching
- `tests.md` — test fixtures and testing against S3
