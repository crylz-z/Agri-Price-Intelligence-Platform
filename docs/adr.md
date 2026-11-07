# Architecture decisions

The constraint behind every entry: a reliable, tested pipeline that costs $0 a month and that one person can run.

## 1. PSA OpenSTAT monthly prices, not DA Bantay Presyo daily
In November 2026 DA's site went unreachable from about 40 test locations worldwide, and it keeps no history, so every outage is a permanent gap. PSA is an official API with region and province data from 2018 that can be downloaded again at any time. The cost is monthly data that arrives about a month late.
- **Not DA PDFs:** that would be the same unreliable host.

## 2. Plain `requests` for ingest, no framework
The source is a documented CSV API that needs about 11 calls a month, so an HTTP client with an honest User-Agent is all the ingest needs.
- **Not dlt or Airbyte:** they're built for many sources and incremental state. dlt was removed from an earlier version because it added a framework and nothing else.
- **Not Scrapling or Playwright:** PSA has no bot wall, and a public pipeline shouldn't evade one.

## 3. Cloudflare R2 for storage
The free tier (10 GB stored, 1M writes, 10M reads a month, egress always free) covers the project. Runs check for one specific file instead of listing the bucket, because listing counts against the write quota.
- **Not AWS S3:** the first version ran on S3 and was paused because of cost.
- **Not Postgres or BigQuery:** a server or warehouse for a few MB of monthly data adds limits, credentials and lock-in.

## 4. Raw is one immutable CSV snapshot per PSA release
PSA revises past months. Keeping `raw/table=<id>/updated=<ts>.csv` exactly as returned lets any number be traced to its release and revisions be measured. The model reads the latest snapshot.
- **Not overwriting a single copy:** it uses less storage but throws away the revision trail.

## 5. DuckDB through `s3fs`
An embedded SQL engine over files on R2 serves dbt, the tests and ad-hoc queries, with no server. The dashboard fetches the 3 MB mart in one GET instead: DuckDB over s3fs took 57 range reads for it.
- **Not Spark:** it's built for data spread across many machines; this is a few MB.
- **Not DuckDB's `httpfs`:** `s3fs` is proven against R2 and shares one config (`src/core/storage.py`) with ingest and the dashboard. It was first chosen when Windows Smart App Control blocked the extension.

## 6. dbt Core 1.x with dbt-duckdb models and tests the data
A staging model and one mart, with dbt tests that fail the run before bad data is published. The mart is written to R2 as Parquet. pytest covers the ingest code.
- **Not plain SQL files:** an earlier version used them, but it would mean rebuilding dbt's dependency order, tests and docs by hand.
- **Not dbt v2:** it's a proprietary Rust binary with "CLI only" DuckDB support and no documented fsspec/R2 access. v1 remains supported and Apache-2.0 licensed.
- **Not Great Expectations or Soda:** a framework to express a handful of checks dbt already runs.

## 7. GitHub Actions daily cron, no orchestrator
One job a day (ingest, then dbt only if something changed) is free on a public repo and emails on failure. A run with no changes costs 1 API call and 11 R2 HEADs. GitHub pauses schedules after 60 days without commits; that loses no data, because PSA keeps history.
- **Not Airflow, Dagster or Prefect:** a scheduler server to host and monitor, for a single two-step job.

## 8. Streamlit on Streamlit Community Cloud for the dashboard
The dashboard is 3 Python pages over four small marts, hosted free from the GitHub repo with a read-only R2 token in Streamlit's secrets. The cost is a wake-up page after 12 hours without visitors.
- **Not Vercel:** it can't run Streamlit's long-running server, so it would mean rewriting the dashboard as a static JavaScript site.
- **Not Evidence or another static DuckDB-WASM site:** no sleep and no keys online, but it replaces tested Python code with a Node build for the same 2 charts.

## 9. Stories are computed in dbt marts, the dashboard only shows them
Year-on-year changes, dish costs and seasonal indexes are tested dbt models published as three small Parquet marts, so every headline number has a test behind it. That adds 3 R2 puts per release day.
- **Not pandas in Streamlit:** the logic would be untested and recomputed on every visitor's session.

## 10. Dish costs stay blank when a staple is unpriced
A province missing one recipe staple gets no dish cost rather than one filled from its region or the country: a filled number would be one PSA never reported. Under half of province dish costs are complete.
- **Not filling from the region:** more map coverage, but a mixed-level number presented as local.

## 11. Story numbers are checked against PSA, not only against our own code
dbt tests recompute year-on-year changes and dish costs from `int_retail_prices` by a separate path, and the `psa_spot_checks` seed holds prices fetched from OpenSTAT's JSON API outside the pipeline; any mismatch blocks the marts. pytest checks the dashboard's headline helpers against a fixture with hand-worked answers. Shape tests alone pass when a join or unit is wrong everywhere.
- **Not shape tests only:** unique keys and positive prices can't catch a wrong commodity mapping or a doubled quantity.

## 12. Three plain dashboard pages, one per mart group (superseded by 13)
The dashboard is a shop window for the pipeline, so each page reads one group of marts (page 1 the staple and dish marts, page 2 the staple mart by area, page 3 the retail and seasonality marts) and uses stock Streamlit and Altair, with tabular digits as the only CSS. Chosen 2026-11-07, after a 5-page version with custom CSS grew to 2,000 lines of view code without making the data more useful.
- **Not the 5-page version:** a separate page for dish costs and another for seasons repeated the same yearly change in many places; dish costs moved to a table on page 1 and seasons to a chart on page 3. It stays in git history at `a7a97b2`.

## 13. The question: how much of the retail peso reaches the farmer, and what a meal costs in wages
Chosen 2026-11-07, because the three lookup pages answered no question. PSA farmgate prices (`2M/NFG`, the same OpenSTAT CSV API as retail) are compared with retail at national and region level for the 18 staples that have a like-for-like farmgate item, with palay converted at PSA's 63% milling recovery rate. Regional minimum wages come from a hand-kept seed of wage orders, which are PDFs with no API, from January 2024 only (about 35 orders instead of 80 back to 2018), and import and price policy from a hand-kept seed of dated policy events. This becomes page 1, ahead of the three existing pages, which stay plain and read one mart group each.
- **Not wholesale (`2M/NWSNEW`):** 10 more tables, about 8 MB a release, and no meat table; farm against retail already shows the gap.
- **Not meat or fish:** PSA publishes no factor from liveweight to retail cut, and fish farmgate is quarterly.
- **Not an import volume series:** monthly BPI arrivals appear only in press reports that disagree with each other.
