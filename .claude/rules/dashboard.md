---
paths:
  - "src/dashboard/**"
  - ".streamlit/**"
---

# Dashboard rules

Before changing anything here, load `developing-with-streamlit` (how to build) and `dashboard-design` (what to build). When they disagree, this file wins, then the user's stated taste. The current layout of each page lives in `src/dashboard/views.py`; read it there.

## Useful first
Every element must help a shopper decide something right away. An element that only describes is cut, or moved into a closed `st.expander`.
- **Headline** on a story page names something actionable, computed from the data ("Repolyo up 34.9%, carrot down 28.5% in a year"), never a count. A count can be the plain line under it.
- **Punch, not detail.** A card holds a name, a big number, one delta and at most one short badge. Explanations go in `help=` tooltips. The baseline is "vs PY" (previous year, same month), explained in the tooltip and never spelled out as a date.
- **Rules, not picks.** Foods, dishes and places on cards are chosen by a rule in `data.py` that runs on each release (biggest fall, biggest rise, …) and is covered by `tests/test_dashboard_data.py`. Never choose them by hand.
- **Like with like.** When ranking foods, rank within a group a shopper compares (e.g. meat against meat). Otherwise one group fills every slot.
- **Plain words** on screen: "everyday foods", "cheapest month to buy", "province", "costs more" / "costs less", "most expensive" (the user finds "dear" and "dearest" stiff). "staple", "basket", "seasonal index" and "geolocation" are code terms. Show PSA's long commodity names only in tooltips.
- Story pages may have a headline and one "how to read it" caption per chart. The Explore page (Look up a price) follows `dashboard-design`'s Wordless rule.

## Honest
- A number shown twice agrees, at the same precision (one-decimal percentages everywhere).
- `—` for no data. A dish or card with a missing input is dropped, not shown as a partial.
- Headline values match the dbt reconciliation tests (ADR 11).

## Data
- All data access goes through `src/dashboard/data.py`. Pages in `views.py` call its helpers, then lay out and chart.
- Helpers take `geo_code` (default the Philippines), so a page follows its region picker. Seasonality is national only.
- `load` caches for 6 h, and the dev server doesn't always reload imported modules, so restart it after editing `data.py`.
- A new mart column a page reads must also be in `tests/fixtures/marts/`, or the page tests fail. Rebuild a fixture by slicing the real mart the same way (see `tests/test_pages.py`).

## Look
- Look comes from `.streamlit/config.toml`, plus custom CSS where it makes a page more striking (the user asked for it). All CSS lives in `app.py` (the `dashboard-no-css` hook keeps `<style>` out of `views.py`); `views.py` emits `st.html` markup with classes, or keyed containers (`.st-key-…`). CSS colours are rgba mid-tones, so they read on both themes.
- **Each page tells its own story with its own chart forms.** A page never reuses another page's main chart; prefer a fresh form (gradient area, usual → now track, quadrant) over another per-food bar list. No heatmaps.
- **Colour has meaning.** Red = costs more, green = costs less, and nothing else. Always pair them with an arrow or sign (`data.arrow`; `st.metric` with a signed delta and `delta_color="inverse"`). Slate blue (`primaryColor`) = selected or informational. Amber = data warning. Food-group hues (`FOOD_HUES`) = kind of food. Every other mark is ink or warm grey.
- **One card style per row**, cards in `st.columns`, with `height="stretch"` so the row stays even. A card is never half empty: fill it with a sparkline or don't stretch it.
- **Lists are one full-width `st.dataframe`** through `views.changes()`, which colours its `vs …` arrow columns, never one `st.markdown` per row. A per-row trend is a `LineChartColumn` (`color="auto-inverse"`, so rising reads red). Prefer a list over a row of KPI cards once a section shows more than two foods.
- **Charts:**
  - Value labels sit right of the bar end or the zero line.
  - Reserve label room in pixels (`Scale(padding=…)`, axis `minExtent`), not as a share of the axis. A share clips on phones, and Vega measures before Inter loads on a cold visit.
  - Food-group colour has no Vega legend (on phones it squeezes the chart); the group goes in the tooltip.
  - d3 formats can't take ₱, so put ₱ in the title.
- Every story page shows the data month in a badge, amber "late" when the month is over 2 months old.
- Foods and dishes never share one selector or chart.
- Light and dark themes, both in `config.toml`; Inter for all text. Streamlit reports the viewer's theme a rerun late, so chart code never branches on it: text and lines take a theme-neutral mid-tone (`MUTED`, `FOOD_HUES`, `DEARER`/`CHEAPER` in `views.py`), and scales use the theme's named ranges (`range="diverging"`, `"category"`). Screenshot new pages with `SCHEME=dark` too.

## Done means
- `pytest` is green, including `tests/test_pages.py`, which renders every page offline.
- You have looked at the screenshots from `scripts/screenshot.py` (1440 and 375 px, fresh server and browser). On this machine set `CHROME=%LOCALAPPDATA%\ms-playwright\chromium-1243\chrome-win64\chrome.exe`. Check: no truncated text, no horizontal scroll, no exceptions.
- The user sees the screenshots and reacts before you move to the next page.

## Hosting
Streamlit Community Cloud (ADR 8) installs from `uv.lock`, runs from the repo root and exposes root-level secrets as environment variables, so `src/core/storage.py` needs no Streamlit-specific code.
