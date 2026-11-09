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
Every headline number comes from a tested dbt model published as a small Parquet mart, so it has a test behind it: today the farmer's share and the verdicts, 2 R2 puts per release day. (First chosen for year-on-year changes, dish costs and seasonal indexes, which ADR 14 dropped.)
- **Not pandas in Streamlit:** the logic would be untested and recomputed on every visitor's session.

## 10. Dish costs stay blank when a staple is unpriced (dish costs dropped by 14)
A province missing one recipe staple gets no dish cost rather than one filled from its region or the country: a filled number would be one PSA never reported. Under half of province dish costs are complete.
- **Not filling from the region:** more map coverage, but a mixed-level number presented as local.

## 11. Story numbers are checked against PSA, not only against our own code
dbt tests recompute the farmer's share, the verdicts and the pass-through by a separate path, and the `psa_spot_checks` seed holds prices fetched from OpenSTAT's JSON API outside the pipeline; any mismatch blocks the marts. pytest checks the dashboard's headline helpers against a fixture with hand-worked answers. Shape tests alone pass when a join or unit is wrong everywhere.
- **Not shape tests only:** unique keys and positive prices can't catch a wrong commodity mapping or a doubled quantity.

## 12. Three plain dashboard pages, one per mart group (superseded by 13)
The dashboard is a shop window for the pipeline, so each page reads one group of marts (page 1 the staple and dish marts, page 2 the staple mart by area, page 3 the retail and seasonality marts) and uses stock Streamlit and Altair, with tabular digits as the only CSS. Chosen 2026-11-07, after a 5-page version with custom CSS grew to 2,000 lines of view code without making the data more useful.
- **Not the 5-page version:** a separate page for dish costs and another for seasons repeated the same yearly change in many places; dish costs moved to a table on page 1 and seasons to a chart on page 3. It stays in git history at `a7a97b2`.

## 13. The question: how much of the retail peso reaches the farmer, and what a meal costs in wages (superseded by 14)
Chosen 2026-11-07, because the three lookup pages answered no question. PSA farmgate prices (`2M/NFG`, the same OpenSTAT CSV API as retail) are compared with retail at national and region level for the 18 staples that have a like-for-like farmgate item, with palay converted at PSA's 63% milling recovery rate. Regional minimum wages come from a hand-kept seed of wage orders, which are PDFs with no API, from January 2024 only (about 35 orders instead of 80 back to 2018), and import and price policy from a hand-kept seed of dated policy events. This becomes page 1, ahead of the three existing pages, which stay plain and read one mart group each.
- **Not wholesale (`2M/NWSNEW`):** 10 more tables, about 8 MB a release, and no meat table; farm against retail already shows the gap.
- **Not meat or fish:** PSA publishes no factor from liveweight to retail cut, and fish farmgate is quarterly.
- **Not an import volume series:** monthly BPI arrivals appear only in press reports that disagree with each other.

## 14. The story is a case file: who takes the pesos between farm and store
Chosen 2026-11-08, because ADR 13's page showed snapshots with no tension: a farmer's share of ₱23 says nothing about change or cause, dish costs can't be split into farm and middle (meat has no farmgate price), and a regional farmer's share mixes supply chains (carrot reads 282% in CALABARZON). The dashboard becomes 1 page, national only: the farmer's share, the pass-through (ADR 15), and the middle's cut against inflation with a verdict computed in dbt on each release, then "Check your food" with the public record (House findings, PCC charges, research), each cited and worded "found", "charged" or "alleged". The marts and seeds no section reads (retail, staple prices, dish costs, seasonality, recipes, wage orders, policy events) are dropped; they stay in git history at `b252e94`. Chosen as 1 page over 2 on 2026-11-08, so a reader new to the topic gets one sentence and one chart per section.
- **Not naming private individuals:** a public page calling a person guilty while cases are open is a libel risk; findings and agencies carry the blame.
- **Not blame from our data alone:** prices show where the pesos go missing, not who takes them; only the record names suspects.
- **Not keeping Overview, Compare places and Look up a food:** they answer no question in the story; one "Check your food" section replaces them.

## 15. Pass-through is measured in pesos, after inflation
Section 2 compares how far the store price moves per peso of farm price move, in months when the farm price rose against months when it fell more than 15% from a year earlier, with both prices deflated by CPI to 2018 pesos. Chosen 2026-11-08 because a critic's first answer to a large middle's cut is "costs rose", and costs that rise in both directions cannot explain a store price that follows the farm price up further than down. Before deflating, the gap read ₱12 up against ₱7 down per ₱10; after, ₱10 against ₱8.
- **Not percentage pass-through:** a fixed peso cost in between makes the store's percentage move smaller than the farm's even in a fair market, so a percentage ratio looks sticky by construction.
- **Not nominal pesos:** general inflation lifts the "up" moves and shrinks the "down" ones, which overstated the gap by half.
- **Not a lag model (error correction):** sounder statistics, but not explainable in one sentence on screen; overlapping year-on-year months make this evidence, not a significance test.

## 16. Wholesale prices split the gap into traders and stores
Chosen 2026-11-08, reversing ADR 13's "Not wholesale", because the story's open question is "who takes the gap?" and farm against store price can't answer it. PSA's wholesale selling price (`2M/NWSNEW`, 8 of its 10 tables, about 5.5 MB a release, monthly since 2010) covers 17 of the 18 foods; kangkong has none. It splits the middle's cut into the trader's cut (wholesale − farm) and the store's cut (store − wholesale), shown in section 1 and "Check your food". The same release adds 3 CPI groups (diesel, transport, electricity and fuels) as a second yardstick in section 2, answering "isn't it just fuel?".
- **Not a new section:** the split changes how section 1 reads, not what a reader concludes overall; diesel sits on section 2's chart.
- **Not the wholesale price index (`PI/WPI`):** it summarises prices we already hold item by item.

## 17. ECharts with a brief entry animation for sections 1 and 3
Chosen 2026-11-09, reversing ADR 12's "stock Streamlit and Altair" for these two charts, because a reader new to the topic should see the typical peso fill up and the store price climb away from the farm price. `st.echarts_chart` ships with Streamlit 1.66, so nothing is installed. The animation runs 0.8 s, plays once and doesn't loop, and the finished frame carries the point alone, since ECharts can't read the viewer's reduced-motion setting. Options are JSON only: no JavaScript formatters, `custom` series or maps. Sections 2 and 4 stay in Altair until the owner has seen the feel.
- **Not Altair transitions:** Vega-Lite has no entry animation.
- **Not Plotly:** a second heavy library for the same two charts, and the developing-with-streamlit skill steers away from it.

## 18. The page tells the story in video order, with big numbers and a scroll reveal
Chosen 2026-11-09 so the page reads like a short video's script, one section per scene, its headline the line said aloud. Section 1 is now the past year's change: foods whose farm price fell while the store price didn't follow (`price_changes_yearly`, tomato −26% against +13% in September 2026). Each story section opens with one or two big numbers (`views.hero`). Every story chart is ECharts (section 4 moved from Altair); "Check your food" stays Altair. `app.py`'s CSS grows from tabular digits to three rules: tabular digits, the big numbers' size and colour, and a scroll-driven fade-in (`animation-timeline: view()`). Browsers without scroll-driven animations, and readers who ask for reduced motion, see the finished chart.
- **Not a custom component with an IntersectionObserver:** it would replay ECharts' own bar growth on scroll, but ships a second copy of ECharts and more JavaScript than the theme button.
- **Not more pages:** each scene would need navigation, and a reader who scrolls keeps reading.
- **A year's change in percent, not pesos:** pork's farm price is for a live hog and its store price for a cut (ADR 13), so only percent changes compare. Pork appears only in section 1 (`seeds/change_only_commodities.csv`).

## 19. One palette for both themes, shared by charts, words and big numbers
Chosen 2026-11-09 after the page showed four blues and two ambers: ECharts colours are fixed in code, while Streamlit darkens `:blue[...]`/`:orange[...]` text 15% and switches it per theme. Now each role has one value in both themes (farmer blue `#4A72E0`, amber `#C77700`, deep amber `#A35400`), each at least 3:1 on both backgrounds. The theme's blue and orange, and their text colours, are set to the same values. The big numbers take their colour through `:blue[...]`/`:orange[...]` in `st.metric`, not CSS, and each headline colours its key words to match.
- **Not a light and a dark value per role:** ECharts can't read the theme, and Streamlit reports it to Python a rerun late, so the bars and the words would drift apart again.
