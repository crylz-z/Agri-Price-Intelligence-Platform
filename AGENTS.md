# AGENTS.md

## Project Overview
Philippine monthly food prices: `src/etl/` saves each PSA OpenSTAT release to Cloudflare R2 and runs dbt (`dbt/`) to build the marts; a Streamlit dashboard (`src/dashboard/`) reads them. Terms: `GLOSSARY.md`. Tool choices: `docs/adr.md`. Unplanned work: `.plans/backlog.md`.

## Quick Start
Run every tool as `uv run python -m <tool>`, as CI and the pre-commit hooks do.
- Check: `uv run python -m pre_commit run --all-files`
- Test: `uv run python -m pytest` (offline)
- Run: `uv run python -m streamlit run src/dashboard/app.py`. Screenshots: `scripts/screenshot.py` (usage in its docstring).
- dbt (reads and writes R2): `uv run python -m dbt.cli.main build --project-dir dbt --profiles-dir dbt`
- Query R2 (read-only): `uv run python -m src.etl.query "SELECT ... FROM shares"`; the views are listed in `src/etl/query.py`.

## Hard Constraints
- **R2 must stay $0/month.** The free tier covers Standard storage only: 10 GB, 1M Class A ops (writes, lists) and 10M Class B ops (reads, HEADs) a month. Keep buckets on Standard, check existence with one HEAD, and write each object once. Flag anything that grows toward those caps.
- **Storage settings come from `src/core/storage.py` only.** DuckDB and dbt reach `s3://` through s3fs, never the `httpfs` extension.
- **Times are Asia/Manila (PHT).**
- **Raw snapshots are immutable.** Ask before overwriting or deleting one.

## Topic Docs
Rules in `.claude/rules/` are the Hard Constraints in full: one file per area, holding that area's conventions, steps and gotchas. Read an area's rule before changing its files. Claude Code also loads each by its `paths:` globs when a matching file is read or edited; work that touches no matching file (a CLI run, a query) misses the load, so read the rule first.
- Pipeline (`.claude/rules/pipeline.md`) — loads on `src/etl/**`, `src/core/**`, `dbt/**`, `.github/workflows/**`; read first before running the pipeline or querying R2
- Dashboard (`.claude/rules/dashboard.md`) — loads on `src/dashboard/**`, `.streamlit/**`
- Tests (`.claude/rules/tests.md`) — loads on `tests/**`
