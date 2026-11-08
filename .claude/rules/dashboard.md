---
paths:
  - "src/dashboard/**"
  - ".streamlit/**"
---

# Dashboard rules

The dashboard is a shop window for the pipeline (ADR 12, 13): 4 plain pages, each reading one group of marts. Pages and URLs are in `GLOSSARY.md` → Dashboard; layout is in `src/dashboard/views.py`. Load `developing-with-streamlit` before changing Streamlit code.

## Scope
- Keep to 4 pages. A new question goes on the page whose mart answers it, as one chart or table with a one-line caption.
- **Plain:** stock Streamlit widgets and Altair charts. The only CSS is tabular digits, in `app.py` (the `dashboard-no-css` hook keeps `<style>` out of `views.py`).
- Page 1 (Farm to plate) answers the thesis: farmer's share and dish wage share. The yearly change ("vs a year ago") belongs on page 2 (Overview). Pages 3 and 4 show price levels, gaps between places and the seasonal pattern.
- A page reads top-down: header → takeaway title → KPI tiles → main chart → breakdowns (the `dashboard-design` skill's order).
- Each caveat sits in the `help=` tooltip of the card it qualifies; a visible caption holds only the month and how to read the chart. An empty state (no data, no wage order) is a caption.

## Honest
- Numbers come from the dbt marts (ADR 9); `data.py` only filters and ranks them, and every helper has a test in `tests/test_dashboard_data.py`.
- Headlines are computed from the data on each release, never written by hand.
- One-decimal percentages everywhere. `—` for no data.
- Plain words on screen: "everyday foods", "costs more", "costs less", "most expensive". "Farm price", "store price" and "policy" stand for farmgate price, retail price and policy event. "Staple", "basket" and "seasonal index" are code terms.

## Colour
Red = costs more, green = costs less, always next to an arrow or a sign (`data.arrow`, or `st.metric` with `delta_color="inverse"`). Everything else is neutral (`MUTED`). Streamlit reports the viewer's theme a rerun late, so a colour must work in both themes: lines and rules take `range="category"` (accent, ink, amber in `.streamlit/config.toml`), which switches with the theme; fixed colours in code are mid-tones, and text drawn on a blue bar is white. A fixed grey line or label fades on the dark background.

## Data
- All data access goes through `src/dashboard/data.py`. Hand-kept seeds the dashboard needs (`staples.csv`, `policy_events.csv`, `farmer_share_exclusions.csv`) are read from the repo, so editing the CSV on `main` is their only upkeep.
- `load` caches for 6 h, and the dev server doesn't always reload imported modules, so restart it after editing `data.py`.
- A new mart column a page reads must also be in `tests/fixtures/marts/`, or the page tests fail.

## Done means
- `pytest` is green, including `tests/test_pages.py`, which renders every page offline.
- You have looked at the screenshots from `scripts/screenshot.py` at 1440 and 375 px: no cut-off text, no horizontal scroll, no exceptions. On this machine set `CHROME=%LOCALAPPDATA%\ms-playwright\chromium-1243\chrome-win64\chrome.exe`. When Google Fonts is unreachable, the screenshots time out "waiting for fonts"; set `STREAMLIT_THEME_FONT=sans-serif STREAMLIT_THEME_HEADING_FONT=sans-serif`.

## Hosting
Streamlit Community Cloud (ADR 8) installs from `uv.lock`, runs from the repo root and exposes root-level secrets as environment variables, so `src/core/storage.py` needs no Streamlit-specific code.
