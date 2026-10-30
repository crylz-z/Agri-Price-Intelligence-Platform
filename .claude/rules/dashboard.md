---
paths:
  - "src/dashboard/**"
  - ".streamlit/**"
---

# Dashboard rules

- The dashboard is frozen. All data access goes through `src/dashboard/utils/data_engine.py` `DataEngine`; pages and components only render DataFrames.
- `DataEngine` reads `clean/` through the `PRICES` subquery, which renames columns to the old page shape: `commodity_group→category`, `commodity_name→commodity`, and `extract_dt` = the posting date as a timestamp. Filter on `posting_date` so DuckDB prunes partitions.
- Methods are wrapped in `st.cache_data`; underscore-prefixed args are excluded from the cache key. They still run outside Streamlit, which `tests/test_data_engine.py` relies on.
- "Today" defaults to Manila time; when the selected date has no data, pages fall back to the latest earlier date (LKGV).
- `enrich_with_geo` adds random lat/lon jitter to markets without coordinates; those pins are not real locations. Remove before any public demo.
- Every uncached query globs `clean/` (R2 list + reads); keep cache TTLs.
