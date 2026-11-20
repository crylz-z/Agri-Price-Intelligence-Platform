---
paths:
  - "src/dashboard/**"
  - ".streamlit/**"
---

# Dashboard rules

The dashboard is one page, "Who's eating the farmer's peso?", for a reader new to the topic (ADR 14). Its sections run in the order a short video would tell them, one scene each (ADR 18): the onion hook, this year, your peso, the middle, the ratchet, "Check your food", the ending (ADR 21). Its sections and on-screen words are in `GLOSSARY.md` → Dashboard; layout is in `src/dashboard/views.py`. Load `developing-with-streamlit` and `dashboard-design` before changing it.

## Scope
- **One page, no navigation.** A new question becomes a section only when it changes what a reader concludes; otherwise it goes in "Check your food" or a `help=` tooltip.
- **A story section is one or two big numbers (`hero`), one computed headline, one line beneath it, one chart and one so-what line under the chart** (`so_what`, computed like the headline: why the chart matters to a shopper). Section 3 is the one exception, with two charts: the typical peso's bar, then each food's farmer centavos, so a food without a wholesale price still fits. The headline is a full sentence a newcomer can repeat.
- **Shares in centavos, price moves in pesos, a change in percent:** "X centavos of every peso" for a share (as USDA's Food Dollar says "cents per dollar"), "₱X" for a real price or price move ("drops ₱10"), "26%" for a year's change or growth since 2018, where meat's live-animal price can't be set peso for peso against a cut (ADR 18, ADR 23).
- **Meat is percent only; fish is by quarter.** Meat never gets a farmer's share or a peso gap. A fish row's month is its quarter's first, so name its period with `views.when` ("July–September 2026").
- **Every sentence opens with a word.** Lead with the noun and put the number after it ("Most foods, 14 of 16, …"), so "₱10. 14 of 16" never reads as "10.14". `test_pages.py` checks every header, line and caption.
- **Plain:** stock Streamlit widgets, `st.echarts_chart` for the story sections 1 to 5 (ADR 17, 18), and Altair for "Check your food". ECharts options are JSON only (no JS formatters, `custom` series or maps) with `theme="streamlit"`, and a `key` so a rerun doesn't replay them. Their entry animation (`views._once`) is 0.8 s, once, never looping, and the finished frame must make the point without the motion. The only CSS is in `app.py` (the `dashboard-no-css` hook keeps `<style>` out of `views.py`): tabular digits, the big numbers' size (keys `hero_<section>_<i>`), and the scroll fade-in on `reveal_<name>` containers, which honours reduced motion. Check motion with Playwright frames taken mid-scroll: a screenshot shows only the finished page. The only JavaScript is the light/dark button in `theme.py`, which writes Streamlit's own theme key in localStorage; check it still flips the page after a Streamlit upgrade.
- **Read in order, the headlines tell the story.** Each is short enough to say aloud; the line beneath it says how to read the chart in plain words, never a colour key like "Amber: X. Grey: Y."
- Each caveat sits in the `help=` tooltip of the headline it qualifies. A visible caption holds only the month, the source or how to read the chart. An empty state is a caption.
- Blame comes only from the public record (`suspects.csv`), worded as its source words it. The data shows a pattern; the tooltips say what else could explain it. The record sits under section 4 and stays off the page (`views.SHOW_RECORD = False`) until the owner has checked its sources by hand.

## Honest
- Numbers come from the dbt marts (ADR 9). `data.py` only filters, scales and ranks them, and every helper has a test in `tests/test_dashboard_data.py`.
- Headlines are computed from the data on each release, never written by hand.
- Plain words on screen: "farm price", "store price", "the gap", "inflation". "Farmgate", "retail", "middle's cut", "CPI", "pass-through", "verdict", "suspicious" and "staple" are code terms.

## Colour
One palette, the same value in light and dark (ADR 19, ADR 21). Blue (`FARM`) is the farmer; amber (`AMBER`) is the middle: traders' part of the peso, the gap between farm and store, the ratchet's climb, the wholesale line. The store price is ink, the theme's text colour: leave a store series uncoloured as the second uncoloured series in its chart (`views.STORE_SLOT`), and the theme's `chartCategoricalColors` gives it the ink in each mode, since Python learns the theme a rerun late. Stores' part of the peso is grey (`STORE_GREY`); everything else is grey (`MUTED`). The theme's `blueColor`/`blueTextColor` equal `FARM` and `orangeColor`/`orangeTextColor` equal `AMBER`, so `:blue[...]` and `:orange[...]` words, the big numbers (`views.paint`) and the bars always match; a test holds them, and the palette's first three slots (blue, ink, amber), together. Each headline colours its key words like its big number (plain, never `**bold**`, which renders lighter inside a header), and the line under it names each colour, so colour never carries meaning alone. Every role colour keeps at least 3:1 on both backgrounds, and text drawn on a blue bar is white. ECharts text left uncoloured takes the theme's ink.

## Data
- All data access goes through `src/dashboard/data.py`. The page reads `farmer_share_monthly`, `food_verdicts`, `price_changes_yearly`, `growth_since_2018` and `change_only_monthly`. `dbt/seeds/suspects.csv` is read from the repo when the public record is on the page, so editing that CSV on `main` is its only upkeep.
- `load` caches for 6 h, and the dev server doesn't always reload imported modules, so restart it after editing `data.py`.
- A new mart column the page reads must also be in `tests/fixtures/marts/`, or the page tests fail. `food_verdicts.parquet`, `price_changes_yearly.parquet`, `growth_since_2018.parquet` and `change_only_monthly.parquet` (with `month` cast to `timestamp[ms]`) there are whole marts, copied from a local build; `farmer_share_monthly.parquet` keeps the months from Sep 2025 plus national red onion in 2023 for the hook. The page tests pin their numbers.

## Done means
- `pytest` is green, including `tests/test_pages.py`, which renders the page offline.
- You have looked at the screenshots from `scripts/screenshot.py` at 1440 and 375 px, light and dark: no cut-off text or legend, no horizontal scroll, no exceptions. On this machine set `CHROME=%LOCALAPPDATA%\ms-playwright\chromium-1243\chrome-win64\chrome.exe`. When Google Fonts is unreachable, the screenshots time out "waiting for fonts"; set `STREAMLIT_THEME_FONT=sans-serif STREAMLIT_THEME_HEADING_FONT=sans-serif`.

## Hosting
Streamlit Community Cloud (ADR 8) installs from `uv.lock`, runs from the repo root and exposes root-level secrets as environment variables, so `src/core/storage.py` needs no Streamlit-specific code.
