# Agri-Price Intelligence Platform

DA Bantay Presyo publishes daily retail food prices for every Philippine region, but keeps no history. This repo captures them twice a day, stores every scrape forever on Cloudflare R2, and publishes one clean, deduplicated, tested table. It costs $0 to run.

```mermaid
graph LR
    DA[("DA Bantay Presyo")] -->|polite scraper| P["pipeline.py<br/>(GitHub Actions cron)"]
    P -->|1 immutable object per run| RAW[("R2 raw/")]
    RAW -->|sql/clean.sql + checks| CLEAN[("R2 clean/")]
    CLEAN -->|DuckDB| UI["Streamlit dashboard"]
```

## How it works
- **Scrape** (`src/etl/scraper.py`): 17 regions × 10 categories, sequential, 1 s apart, with an honest User-Agent. A failed category doesn't fail its region; 6 failed requests in a row stop the run.
- **Raw** (`raw/scrape_date=YYYY-MM-DD/run=HHMMSS.parquet`): exactly what was scraped, never changed.
- **Clean** (`clean/posting_date=YYYY-MM-DD/prices.parquet`): one row per posting date, region, market and commodity; the latest scrape wins. Only the posting dates a run touched are rebuilt, from the last 14 days of raw.
- **Checks** (`src/etl/checks.py`): no duplicate or null keys, prices > 0, no future posting dates, at least 15 of 17 regions, and no sudden drop in row count. A failed check fails the run, and GitHub emails the failure; clean is left untouched. A region DA hasn't updated for over 14 days only warns.
- **$0 on R2**: about 4 Class A operations per run, a few MB per month. See `docs/cloudfare-agent-notes/free-tier-r2.md`.

## Run it
Needs [uv](https://docs.astral.sh/uv/). Copy `.env.example` to `.env` and fill in an R2 bucket and API token.

```bash
uv sync
uv run python -m pre_commit install  # ruff + mypy on every commit
uv run python -m pytest            # tests, no network (CI runs them on PRs)
uv run python -m src.etl.pipeline  # scrape and publish
uv run python -m streamlit run src/dashboard/app.py
```

---
Data: [DA Bantay Presyo](http://www.bantaypresyo.da.gov.ph/).
