---
paths:
  - "src/dashboard/**"
  - ".streamlit/**"
---

# Dashboard rules

The dashboard is a shop window for the pipeline (ADR 12): 3 plain pages, each reading one group of marts. Pages and URLs are in `GLOSSARY.md` → Dashboard; layout is in `src/dashboard/views.py`. Load `developing-with-streamlit` before changing Streamlit code.

## Scope
- Keep to 3 pages. A new question goes on the page whose mart answers it, as one chart or table with a one-line caption.
- **Plain:** stock Streamlit widgets and Altair charts. The only CSS is tabular digits, in `app.py` (the `dashboard-no-css` hook keeps `<style>` out of `views.py`).
- The yearly change ("vs a year ago") belongs on page 1 (Overview). Pages 2 and 3 show price levels, gaps between places and the seasonal pattern.

## Honest
- Numbers come from the dbt marts (ADR 9); `data.py` only filters and ranks them, and every helper has a test in `tests/test_dashboard_data.py`.
- Headlines are computed from the data on each release, never written by hand.
- One-decimal percentages everywhere. `—` for no data.
- Plain words on screen: "everyday foods", "costs more", "costs less", "most expensive". "Staple", "basket" and "seasonal index" are code terms.

## Colour
Red = costs more, green = costs less, always next to an arrow or a sign (`data.arrow`, or `st.metric` with `delta_color="inverse"`). Everything else is neutral (`MUTED`). Colours drawn in code are mid-tones that read on both the light and dark themes, because Streamlit reports the viewer's theme a rerun late.

## Data
- All data access goes through `src/dashboard/data.py`.
- `load` caches for 6 h, and the dev server doesn't always reload imported modules, so restart it after editing `data.py`.
- A new mart column a page reads must also be in `tests/fixtures/marts/`, or the page tests fail.

## Done means
- `pytest` is green, including `tests/test_pages.py`, which renders every page offline.
- You have looked at the screenshots from `scripts/screenshot.py` at 1440 and 375 px: no cut-off text, no horizontal scroll, no exceptions. On this machine set `CHROME=%LOCALAPPDATA%\ms-playwright\chromium-1243\chrome-win64\chrome.exe`. When Google Fonts is unreachable, the screenshots time out "waiting for fonts"; set `STREAMLIT_THEME_FONT=sans-serif STREAMLIT_THEME_HEADING_FONT=sans-serif`.

## Hosting
Streamlit Community Cloud (ADR 8) installs from `uv.lock`, runs from the repo root and exposes root-level secrets as environment variables, so `src/core/storage.py` needs no Streamlit-specific code.
