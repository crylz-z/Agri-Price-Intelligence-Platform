# Architecture decisions

The constraint behind every entry: a reliable, tested pipeline that costs $0 a month and that one person can run. Format and gate: `.claude/skills/domain-modeling/ADR-FORMAT.md`.

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
- **Not DuckDB's `httpfs`:** Windows Smart App Control blocked the extension during development, and `s3fs` was proven against R2.

## 6. dbt Core 1.x with dbt-duckdb models and tests the data
A staging model and one mart, with dbt tests that fail the run before bad data is published. The mart is written to R2 as Parquet. pytest covers the ingest code.
- **Not plain SQL files:** an earlier version used them, but it would mean rebuilding dbt's dependency order, tests and docs by hand.
- **Not dbt v2:** it's a proprietary Rust binary with "CLI only" DuckDB support and no documented fsspec/R2 access. v1 remains supported and Apache-2.0 licensed.
- **Not Great Expectations or Soda:** a framework to express a handful of checks dbt already runs.

## 7. GitHub Actions daily cron, no orchestrator
One job a day (ingest, then dbt only if something changed) is free on a public repo and emails on failure. A run with no changes costs 1 API call and 11 R2 HEADs. GitHub pauses schedules after 60 days without commits; that loses no data, because PSA keeps history.
- **Not Airflow, Dagster or Prefect:** a scheduler server to host and monitor, for a single two-step job.
