# CLAUDE.md

Philippine monthly retail food prices: `src/etl/` saves each PSA OpenSTAT release to Cloudflare R2 and runs dbt (`dbt/`) to build the marts; a Streamlit dashboard (`src/dashboard/`) reads them. Terms: `GLOSSARY.md`. Tool choices: `docs/adr.md`.

## Commands
Run every tool as `uv run python -m <tool>`, as CI and the pre-commit hooks do.
- Before reporting done: `uv run python -m pytest` and `uv run python -m pre_commit run --all-files`.
- Query R2 (read-only): `uv run python -m src.etl.query "SELECT ... FROM shares"`. Views and their marts are listed in `src/etl/query.py`.
- Dashboard: `uv run python -m streamlit run src/dashboard/app.py`. Screenshots: `scripts/screenshot.py` (usage in its docstring).
- dbt (reads and writes R2): `uv run python -m dbt.cli.main build --project-dir dbt --profiles-dir dbt`.

## Hard constraints
- **R2 must stay $0/month.** Follow `docs/cloudfare-agent-notes/free-tier-r2.md`: no Infrequent Access, no `ListObjects` or overwrite loops. Flag anything that grows storage toward 10 GB or Class A ops toward 1M/month.
- **Storage settings come from `src/core/storage.py` only.** DuckDB and dbt reach `s3://` through s3fs, never the `httpfs` extension.
- **Times are Asia/Manila (PHT).**
- **Raw snapshots are immutable.** Never overwrite or delete one without asking.

## Workflow
`/grill-with-docs` → `/to-spec` → `/to-tickets` → `/implement` (one ticket per session, `/clear` between). Each piece of work lives in `.plans/<slug>/`: `spec.md` plus one `NN-<slug>.md` per ticket, whose `Status:` and `## Notes` carry progress between sessions. Work not yet specced is in `.plans/backlog.md`; delete a plan once it ships; git history keeps it.

## Docs
- Before editing any Markdown doc, load the `writing-for-agents` skill.
- `.claude/rules/` holds durable, general rules, and each file loads when you touch its paths (`pipeline.md`, `dashboard.md`, `tests.md`). Add a rule there only when a general rule changes. The current behaviour lives in the code, and progress lives in the tickets.
