# PH Food Prices

When food gets expensive, the farmer often isn't the one getting the money. For 25 everyday foods (vegetables, rice, eggs, fish and meat), this dashboard shows how many centavos of every peso at the store reach the farmer, how much traders' part grew since 2018, and whether store prices come down when farm prices fall. It opens on the 2023 onion crisis.

It is built on monthly retail, wholesale and farmgate food prices for the Philippines (retail: national, 18 regions and 100 provinces and cities, 197 commodities, from January 2018) and the consumer price index (all items, diesel, transport, electricity and fuels), all from the Philippine Statistics Authority. A daily job stores each PSA release unchanged on Cloudflare R2, a dbt project models and tests it, and a one-page Streamlit dashboard shows the result. It costs $0 to run.

**Live dashboard:** [ph-food-prices.streamlit.app](https://ph-food-prices.streamlit.app/)

```mermaid
graph LR
    PSA[("PSA OpenSTAT API")] -->|ingest.py, only new releases| RAW[("R2 raw/<br/>1 CSV snapshot per release")]
    RAW -->|dbt build: staging, intermediate, tests| MART[("R2 mart/<br/>5 Parquet marts")]
    MART --> UI["Streamlit dashboard<br/>1 page"]
    CRON["GitHub Actions<br/>daily cron"] -.-> PSA
```

## How it works
- **Ingest** (`src/etl/ingest.py`): one GET per PSA folder lists the 11 retail price tables, the 9 farmgate tables (fish is quarterly), the 9 wholesale tables and the 1 CPI table used, with their `updated` time. A table is downloaded only when R2 doesn't have that release yet, checked with a single HEAD. A day with no new release makes 4 PSA calls and 30 HEADs.
- **Raw** (`raw/table=<id>/updated=<YYYYMMDDTHHMMSS>.csv`): each table exactly as PSA returned it, never rewritten. PSA revises past months, so keeping every release makes each number traceable to its source.
- **Model** (`dbt/`, dbt Core + dbt-duckdb):
  - Staging unpivots the month columns of the latest snapshots: `stg_psa__retail_prices`, `stg_psa__farmgate_prices` (months, or quarters for fish), `stg_psa__wholesale_prices`, `stg_psa__cpi` (national, 4 groups).
  - `int_retail_prices` adds PSGC geo codes from a seed; `int_staple_prices` keeps the 28 everyday foods in `staples.csv`.
  - `farmer_share_monthly`: for 21 staples, the farmgate price over the retail price, national and by region, by month (`int_farmer_share`). Fish (bangus, tilapia, galunggong) has a farm price by quarter, set against the quarter's average store price. Where PSA has a wholesale price (20 staples), it splits the gap into the trader's cut (wholesale − farm) and the store's cut (store − wholesale).
  - `food_verdicts`: one row per staple. It holds the middle's cut in 2018 and over the last 12 months, against CPI over the same span (plus diesel, transport and fuel CPI for context), and the verdict (suspicious when the cut grew more than 5 points faster). It also holds the pass-through, in 2018 pesos: how far the store price moves per peso the farm price moves, in months when the farm price rose or fell by over 15%.
  - `price_changes_yearly`: one row per food, national: the farm and store price in the latest month (fish: quarter) against a year earlier, as percent changes. It adds meat (pork kasim and liempo, whole chicken, beef) against PSA's live-animal price (`seeds/change_only_commodities.csv`), which compares only as a percent change.
  - `growth_since_2018`: one row per food, national: the farm and store price's growth from 2018 to the last 12 months, meat included, with inflation over the same months.
  - `change_only_monthly`: those change-only foods (meat) by month, national, for the meat chart in "Check your food".
  - dbt tests recompute the farmer's share, the wholesale split, the verdicts, the pass-through and the growth since 2018 by a separate path, and check prices against values fetched from PSA by hand (`psa_spot_checks.csv`, `psa_farmgate_spot_checks.csv`, and wholesale and CPI values inside their tests).
- **Tests that block publishing**:
  - a table or geolocation is missing, or PSA adds an unknown one
  - duplicate keys
  - `price <= 0`
  - a release with far fewer filled cells than the one before

  All tests run upstream of the marts, so a failure skips the write and R2 keeps the last good mart. Three checks only warn: a latest month more than 3 months old, a national price that doubles or halves in a month, and a farmer's share above 100%.
- **pytest** covers ingest (change detection, HEAD-only R2 checks, rejecting non-CSV responses), the pipeline's dbt trigger, the dashboard's data layer and an offline render of the page, all without network.
- **Dashboard** (`src/dashboard/`), one page, "Who's eating the farmer's peso?". Its sections run in the order a short video would tell them. Each opens with one or two big numbers, then one computed headline, one chart (two in section 3) and a so-what line. The story charts are ECharts with a brief entry animation and fade in as they scroll into view. Blue is the farmer, amber the middle (traders and the gap), and the store price is ink:
  1. The hook: the 2023 onion crisis, store ₱468 against farm ₱216 in January, then the farm price's crash.
  2. This year: the foods whose farm price fell over the past year, beside their store price (meat as percent changes only, fish by quarter).
  3. Of a typical peso at the store, how many centavos reach the farmer, traders and stores, then the farmer's centavos per food.
  4. The middle: traders' centavos of a peso in 2018 and now, then each food's farm and store growth since 2018 against inflation.
  5. When the farm price falls ₱10, how far the store price falls, against when it rises ₱10, drawn as an example.
  6. Check your food: one food's prices, its numbers, and its farmer's share against the typical food's. Meat shows its live-animal and cut prices, then how each moved since 2018.
  7. A one-line ending.

  `suspects.csv` (the public record) is off the page until its sources are checked by hand. Streamlit Community Cloud updates on every push to `main`.
- **$0 on R2**: a release day has up to 30 snapshot writes and 5 mart writes, plus about 30 HEADs a day, well inside the free tier. See `docs/cloudfare-agent-notes/free-tier-r2.md`. The reasons behind each tool are in `docs/adr.md`; the terms are defined in `GLOSSARY.md`.

## Run it
Needs [uv](https://docs.astral.sh/uv/). Copy `.env.example` to `.env` and fill in an R2 bucket and API token.

```bash
uv sync
uv run python -m pre_commit install   # ruff + mypy on every commit
uv run python -m pytest               # no network
uv run python -m src.etl.pipeline     # ingest; dbt build only if PSA released something
uv run python -m src.etl.pipeline --build   # always run dbt
uv run python -m streamlit run src/dashboard/app.py
```

To rehearse the Streamlit Community Cloud deploy, paste the app's Secrets TOML into `.streamlit/secrets.toml` (gitignored) and run the dashboard. Its root-level keys become environment variables and take precedence over `.env`, as on the cloud.

dbt on its own, from the repo root:

```bash
uv run python -m dbt.cli.main build --project-dir dbt --profiles-dir dbt
# against a local copy of raw/ (needs <dir>/mart/ to exist):
uv run python -m dbt.cli.main build --project-dir dbt --profiles-dir dbt --vars "{lake_root: '<dir>'}"
```

## Sample queries
`src/etl/query.py` runs read-only SQL over the `raw`, `shares`, `verdicts`, `changes`, `change_only` and `growth` views:

```bash
# National farmer's share of red onion, last 12 months
uv run python -m src.etl.query "SELECT month, farmer_share FROM shares WHERE geo_code = '000000000' AND staple = 'Red onion' ORDER BY month DESC LIMIT 12"

# Foods whose store price falls least when the farm price falls
uv run python -m src.etl.query "SELECT staple, up_pass_through, down_pass_through FROM verdicts ORDER BY down_pass_through"

# Which release each table's latest snapshot comes from
uv run python -m src.etl.query "SELECT \"table\", max(updated) FROM raw GROUP BY ALL ORDER BY 1"
```

## What I'd build next
- **Who feels it most:** PSA's CPI for the bottom 30% of households (`PI/BIH`).
- **Revision tracker:** diff consecutive snapshots to show which past months PSA revised.

---
Data: [PSA OpenSTAT](https://openstat.psa.gov.ph/): Retail Prices of Agricultural Commodities by Geolocation, Commodity, Year and Period (2018 onward), the Farmgate Prices tables (folder `NFG`), the Wholesale Selling Prices tables (folder `NWSNEW`) and the Consumer Price Index for All Income Households (2018=100).
