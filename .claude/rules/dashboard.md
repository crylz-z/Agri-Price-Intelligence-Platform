---
paths:
  - "src/dashboard/**"
  - ".streamlit/**"
---

# Dashboard rules

- All data access is `src/dashboard/data.py`: `load_mart()` fetches the mart in one `cat_file` (1 GET) and caches it for 6 h with `st.cache_data`. Pages in `views.py` only filter and chart DataFrames; keep filtering helpers in `data.py`, where `tests/test_dashboard_data.py` covers them.
- `app.py` only wires `st.navigation`. Test a page with `AppTest.from_string("from src.dashboard.views import trend_page\ntrend_page()")`; `AppTest.switch_page` can't reach function pages.
- Scope is 2 pages (trend, area comparison). New pages and hosting are backlog items in the spec.
