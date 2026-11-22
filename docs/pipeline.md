# How the pipeline works

The detail behind the [README](../README.md). Rules for changing the pipeline are in `.claude/rules/pipeline.md`.

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
- **pytest** covers ingest (change detection, HEAD-only R2 checks, rejecting non-CSV responses), the pipeline's dbt trigger, the dashboard's data layer and an offline render of each page, all without network.
- **Dashboard** (`src/dashboard/`), five pages under a top navigation, each section a headline, at most one line and a so-what line. The story charts are ECharts with a brief entry animation. Blue is the farmer, amber the middle (traders and the gap), and the store price is ink:
  1. **The story** (`/`): the newest month's biggest move in a farmer's share; the 2023 onion crisis, where the reader guesses the store price before the page shows it; who stands between farm and store; a receipt splitting the reader's own basket (an example until they change it) between farmer, traders and stores; traders' centavos of a peso in 2018 and now; an example where the farm price goes up and back down and the store price ratchets up; and the total regulators have fined so far.
  2. **Who got caught** (`/caught`): each food's farmer centavos and farm and store growth since 2018, then the public record (`dbt/seeds/suspects.csv`), rulings first, and what can be done, with a button to report a cartel to the Philippine Competition Commission.
  3. **Check your food** (`/food?food=…`): one food's prices, its numbers, and its farmer's share against the typical food's. Meat shows its live-animal and cut prices, then how each moved since 2018. Under every food, its last 12 months against the usual range for each month (`seasonal_baseline`).
  4. **The short version** (`/short`): the whole finding as plain bullets, no charts, then links to the proof and to the reader's own food.
  5. **How it's built** (`/how`): this pipeline as a picture, the latest PSA release and the repo link.

  Streamlit Community Cloud updates on every push to `main`.
- **$0 on R2**: a release day has up to 30 snapshot writes and 6 mart writes, plus about 30 HEADs a day, well inside the free tier. See [R2 pricing](https://developers.cloudflare.com/r2/pricing/). The reasons behind each tool are in [adr.md](adr.md); the terms are defined in [GLOSSARY.md](../GLOSSARY.md).

## Rehearse the deploy, run dbt alone
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
