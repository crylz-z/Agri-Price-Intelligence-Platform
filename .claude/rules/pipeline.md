---
paths:
  - "src/etl/**"
  - "src/core/**"
  - "sql/**"
  - ".github/workflows/**"
---

# Pipeline rules

## Layer contract
- Raw: `s3://$S3_BUCKET_NAME/raw/scrape_date=YYYY-MM-DD/run=HHMMSS.parquet`, one object per run, never rewritten. Schema is `pipeline.RAW_SCHEMA`.
- Clean: `clean/posting_date=YYYY-MM-DD/prices.parquet`. Key `(posting_date, region_id, market_name, commodity_name)`, latest `extract_dt` wins. Built by `sql/clean.sql` from raw scrape dates back to `min(today - 14 days, oldest posting_date in the run)`; only posting dates in this run are rewritten. The wider window matters: a stale region rebuilds an old posting date, and a 14-day window would drop other regions' rows for it.
- Checks: a future posting date is an error; a region whose latest posting is over 14 days old is a warning (DA leaves some regions unposted for weeks, e.g. BARMM 51 days on 2026-10-30). Posting date is per region, identical across all 10 categories (checked live 2026-10-30).
- Order in `pipeline.run`: 0 rows → fail; write raw; build clean in memory; `checks.check`; write clean only if there are no errors.

## Scraper
- `commodity_name` is `"<name> - <specifications>"`; `commodity_group` is the `CATEGORY_MAP` name.
- `posting_date` is parsed from the date endpoint (`"October 28, 2026"`); an unparsable date fails that region.
- Every `tbl_price_get_comm_*_rice.php` endpoint serves any category id 1–10; an empty id returns nothing. Market names are `<th class="text-wrap">` cells; `N/A` cells are skipped. A repeated market name (Region III lists Baler, Tarlac City and San Jose City twice, each column with its own prices) becomes `"<name> #2"` in column order; raw before 2026-10-31 has the unlabelled duplicates.
- Honest bot: fixed `apip/<version>` User-Agent, sequential, fixed delay. Don't add UA rotation, spoofed headers or jitter. robots.txt was 404 on 2026-10-30.

## Known limits
- `_raw_paths` lists all of `raw/` in one paginated call; revisit past ~5000 objects.
- The price outlier warning uses 10× the commodity median; replace with per-commodity ceilings once 2 weeks of data exist.
- Cadence review due ~2026-11-13: measure `extract_dt - posting_date` per region in raw and pick the run frequency.
