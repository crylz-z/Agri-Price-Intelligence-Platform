---
paths:
  - "src/etl/**"
  - "src/core/**"
  - "dbt/**"
  - ".github/workflows/**"
---

# Pipeline rules

## Layer contract
- Raw: `s3://$S3_BUCKET_NAME/raw/table=<id>/updated=<YYYYMMDDTHHMMSS>.csv`, one per PSA release, stored as returned (Windows-1252, CRLF, missing values `.`, `..` or `...`), never rewritten. `<id>` drops PSA's `.px`; `updated` is PSA's timestamp without separators. Retail, farmgate, wholesale and CPI tables share this prefix.
- Marts, rebuilt whole by dbt from the latest snapshot per table: `mart/farmer_share_monthly.parquet` (key `month, geo_code, staple`), `mart/food_verdicts.parquet` (`staple`), `mart/price_changes_yearly.parquet` (`staple`), `mart/growth_since_2018.parquet` (`staple`) and `mart/change_only_monthly.parquet` (`month, staple`). Older marts on R2 (`retail_prices_monthly`, `staple_prices_monthly`, `dish_costs_monthly`, `staple_seasonality`) are no longer written.
- Order in `pipeline.main`: ingest; if it wrote anything (or `--build`), `dbt build`; a failed build exits 1.

## Ingest (`src/etl/ingest.py`)
- Change detection is `storage.exists`: one HEAD. Never use s3fs `exists()`/`info()` on R2: a miss adds a ListObjects (Class A). Never list R2 in ingest.
- Four PSA folders: every retail table in `2018NEW`, only `FARMGATE_TABLES` in `NFG`, only `WHOLESALE_TABLES` in `NWSNEW`, and only `CPI_TABLES` in `PI/CPI/2018NEW`. Each dict must match its seed (`seeds/psa_<kind>_tables.csv`); a pytest checks it.
- The CPI table is 120 places x 354 groups, so `CPI_QUERY` asks for PHILIPPINES (code `0`) and the 4 `CPI_GROUPS` codes: all items, electricity and fuels, transport, diesel. `assert_cpi_groups_expected` fails if PSA renumbers the codes. Changing `CPI_GROUPS` needs a new snapshot, but the path depends only on PSA's `updated`, so ingest skips the table until PSA's next CPI release.
- `download` accepts only a body that starts with its table's own CSV header (`Table.header`: PSA lays farmgate tables out differently), so an error page can't become an immutable snapshot.
- Honest bot: fixed `ph-food-prices/<version>` User-Agent, sequential, 1 s delay. Cloudflare 403s bare `urllib` but serves `requests` with this UA. Don't add UA rotation, spoofed headers or jitter.

## dbt (`dbt/`)
- R2 access goes through the plugin `src/etl/dbt_storage.py` → `storage.configure_duckdb`; don't put S3 settings in `profiles.yml`.
- `external` models are written **before** their own tests run. Put every blocking test on `stg_`/`int_` (table) models, so a failure skips the mart and R2 keeps the last good one.
- `psa_snapshot_files(kind=…)` picks the newest snapshots per table with one `glob()` (1 list); staging reads only those files. `farmgate`, `wholesale` and `cpi` mean listed in `seeds/psa_<kind>_tables.csv`, and every other table is `retail`, so a new PSA retail table still trips the retail tests. The calling model needs `-- depends_on:` on all three seeds (copy the line from a staging model).
- dbt's profile is `:memory:`, so intermediate models can't be queried after a build; run the compiled SQL from `dbt/target/compiled/` in DuckDB instead.
- `var('verdict_margin')` (0.05, chosen with the owner 2026-11-08): a staple is suspicious when its middle's cut grew more than 5 points faster than CPI.
- `var('move_threshold')` (0.15): a month counts toward the pass-through when its farm price, in 2018 pesos, moved more than 15% from a year earlier (ADR 15).
- Retail geo codes come from `seeds/geolocations.csv` (PSGC, from table metadata on 2026-11-02, identical in all 11 retail tables). PSA's label case differs across tables (`Philippines` vs `PHILIPPINES`): join on `lower()`.
- Farmgate quirks, handled in `stg_psa__farmgate_prices` and `int_farmer_share`:
  - Region labels differ from retail and some carry a footnote mark (`1/`): strip it and map through `seeds/farmgate_geolocations.csv`.
  - Province price cells carry footnote marks, so staging drops province rows before the cast.
  - `0.00` means no sales, not a price: the share keeps `price > 0` only.
  - `seeds/farmer_share_exclusions.csv` drops a staple and place pair: in every month when `month` is blank (bundle vs kg units), or that month only, for a national price no regional price supports (pechay, Jan–Mar 2026). Add a month only with the owner, and give its reason.
  - AFN11 names its commodity column `Type`; EFGP0 puts `Commodity` first.
  - Fish (`0152M4GFPF0`) is quarterly ("2018 Quarter 3"), with a `Species` column indented under ALL SPECIES and one misspelt region ("Nothern Mindanao", mapped in the seed). `union_by_name` gives every table every period column, so staging keeps quarters only where `Species` is set. A fish row is one quarter (`months_in_period` 3, `month` its first); `int_farmer_share` sets it against the quarter's average retail and wholesale price when all three months exist, and the pass-through leaves it out (ADR 22).
  - Meat's farm price is a live animal (`Hog for Slaughter`, `Broiler Chicken`, `Cattle for Slaughter` in AFN11), so meat lives in `seeds/change_only_commodities.csv` (with `farm_name` and `store_name` for the page) and never in `int_farmer_share`.
  - Units are PSA's stated unit: pesos per kg for most, per piece for eggs.
- Wholesale (`stg_psa__wholesale_prices`, `seeds/wholesale_commodities.csv`): same layout and region labels as farmgate (joined through `farmgate_geolocations`), with no footnote marks or 0.00 cells seen on 2026-11-08. Rice is milled and egg per piece, so no yield conversion. Kangkong has none. The trader's and store's cuts can dip below 0 in a month; the dashboard clips them for drawing only.
- `lake_root` var overrides `s3://$S3_BUCKET_NAME` for a local build; DuckDB won't create the local `mart/` folder.

## Known limits
- A failed `dbt build` isn't retried: the next day's ingest finds nothing new, so it skips dbt. Rerun the "Daily PSA Prices" workflow by hand with **build** ticked.
- GitHub turns off a scheduled workflow after 60 days with no commits to the repo.
- GitHub starts scheduled runs late, by up to 8 hours in November 2026 (a 10:00 PHT cron ran at 17:00–18:30 PHT), and it can drop them at peak load. The cron (01:37 PHT) sits off the hour to dodge the busiest slot.
- Staging reads 2 snapshots × 29 tables (11 retail, about 12 MB a snapshot set; 9 farmgate, about 16 MB with fish; 9 wholesale, about 7.5 MB with fish) from R2 on each build, about 71 MB. Wholesale adds about 66 MB of raw storage a year. Retail alone took about 20 s; the farmgate share is not yet timed on R2.
- DuckDB over s3fs reads Parquet in many small range requests (57 for the 3 MB mart). Code that reads the whole mart should `cat_file` it once, as `src/dashboard/data.py` does.
