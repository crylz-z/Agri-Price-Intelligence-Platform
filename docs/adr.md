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
Every headline number comes from a tested dbt model published as a small Parquet mart, so it has a test behind it: today the farmer's share and the verdicts, 2 R2 puts per release day.
- **Not pandas in Streamlit:** the logic would be untested and recomputed on every visitor's session.

## 11. Story numbers are checked against PSA, not only against our own code
dbt tests recompute the farmer's share, the verdicts and the pass-through by a separate path, and the `psa_spot_checks` seed holds prices fetched from OpenSTAT's JSON API outside the pipeline; any mismatch blocks the marts. pytest checks the dashboard's headline helpers against a fixture with hand-worked answers. Shape tests alone pass when a join or unit is wrong everywhere.
- **Not shape tests only:** unique keys and positive prices can't catch a wrong commodity mapping or a doubled quantity.

## 14. The story is a case file: who takes the pesos between farm and store
Chosen 2026-11-08, because the earlier page showed snapshots with no tension: a farmer's share of ₱23 says nothing about change or cause, dish costs can't be split into farm and middle (meat has no farmgate price), and a regional farmer's share mixes supply chains (carrot reads 282% in CALABARZON). The dashboard becomes 1 page, national only: the farmer's share, the pass-through (ADR 15), and the middle's cut against inflation with a verdict computed in dbt on each release, then "Check your food" with the public record (House findings, PCC charges, research), each cited and worded "found", "charged" or "alleged". The marts and seeds no section reads (retail, staple prices, dish costs, seasonality, recipes, wage orders, policy events) are dropped; they stay in git history at `b252e94`. Chosen as 1 page over 2 on 2026-11-08, so a reader new to the topic gets one sentence and one chart per section.
- **Not naming private individuals:** a public page calling a person guilty while cases are open is a libel risk; findings and agencies carry the blame.
- **Not blame from our data alone:** prices show where the pesos go missing, not who takes them; only the record names suspects.
- **Not keeping Overview, Compare places and Look up a food:** they answer no question in the story; one "Check your food" section replaces them.

## 15. Pass-through is measured in pesos, after inflation
Section 2 compares how far the store price moves per peso of farm price move, in months when the farm price rose against months when it fell more than 15% from a year earlier, with both prices deflated by CPI to 2018 pesos. Chosen 2026-11-08 because a critic's first answer to a large middle's cut is "costs rose", and costs that rise in both directions cannot explain a store price that follows the farm price up further than down. Before deflating, the gap read ₱12 up against ₱7 down per ₱10; after, ₱10 against ₱8.
- **Not percentage pass-through:** a fixed peso cost in between makes the store's percentage move smaller than the farm's even in a fair market, so a percentage ratio looks sticky by construction.
- **Not nominal pesos:** general inflation lifts the "up" moves and shrinks the "down" ones, which overstated the gap by half.
- **Not a lag model (error correction):** sounder statistics, but not explainable in one sentence on screen; overlapping year-on-year months make this evidence, not a significance test.

## 16. Wholesale prices split the gap into traders and stores
Chosen 2026-11-08, because the story's open question is "who takes the gap?" and farm against store price can't answer it. PSA's wholesale selling price (`2M/NWSNEW`, 8 of its 10 tables, about 5.5 MB a release, monthly since 2010) covers 17 of the 18 foods; kangkong has none. It splits the middle's cut into the trader's cut (wholesale − farm) and the store's cut (store − wholesale), shown in section 1 and "Check your food". The same release adds 3 CPI groups (diesel, transport, electricity and fuels) as a second yardstick in section 2, answering "isn't it just fuel?".
- **Not a new section:** the split changes how section 1 reads, not what a reader concludes overall; diesel sits on section 2's chart.
- **Not the wholesale price index (`PI/WPI`):** it summarises prices we already hold item by item.

## 17. ECharts with a brief entry animation for sections 1 and 3
Chosen 2026-11-09, replacing Altair for these two charts, because a reader new to the topic should see the typical peso fill up and the store price climb away from the farm price. `st.echarts_chart` ships with Streamlit 1.66, so nothing is installed. The animation runs 0.8 s, plays once and doesn't loop, and the finished frame carries the point alone, since ECharts can't read the viewer's reduced-motion setting. Options are JSON only: no JavaScript formatters, `custom` series or maps. Sections 2 and 4 stay in Altair until the owner has seen the feel.
- **Not Altair transitions:** Vega-Lite has no entry animation.
- **Not Plotly:** a second heavy library for the same two charts, and the developing-with-streamlit skill steers away from it.

## 18. The page tells the story in video order, with big numbers and a scroll reveal
Chosen 2026-11-09 so the page reads like a short video's script, one section per scene, its headline the line said aloud. Section 1 is now the past year's change: foods whose farm price fell while the store price didn't follow (`price_changes_yearly`, tomato −26% against +13% in September 2026). Each story section opens with one or two big numbers (`views.hero`). Every story chart is ECharts (section 4 moved from Altair); "Check your food" stays Altair. `app.py`'s CSS grows from tabular digits to three rules: tabular digits, the big numbers' size and colour, and a scroll-driven fade-in (`animation-timeline: view()`). Browsers without scroll-driven animations, and readers who ask for reduced motion, see the finished chart.
- **Not a custom component with an IntersectionObserver:** it would replay ECharts' own bar growth on scroll, but ships a second copy of ECharts and more JavaScript than the theme button.
- **Not more pages:** each scene would need navigation, and a reader who scrolls keeps reading.
- **A year's change in percent, not pesos:** pork's farm price is for a live hog and its store price for a cut, so only percent changes compare. Pork appears only in section 1 (`seeds/change_only_commodities.csv`).

## 19. One palette for both themes, shared by charts, words and big numbers
Chosen 2026-11-09 after the page showed four blues and two ambers: ECharts colours are fixed in code, while Streamlit darkens `:blue[...]`/`:orange[...]` text 15% and switches it per theme. Now each role has one value in both themes (farmer blue `#4A72E0`, amber `#C77700`, deep amber `#A35400`), each at least 3:1 on both backgrounds. The theme's blue and orange, and their text colours, are set to the same values. The big numbers take their colour through `:blue[...]`/`:orange[...]` in `st.metric`, not CSS, and each headline colours its key words to match.
- **Not a light and a dark value per role:** ECharts can't read the theme, and Streamlit reports it to Python a rerun late, so the bars and the words would drift apart again.

## 20. Pork in "Check your food" as a change since 2018, never pesos side by side
Chosen 2026-11-09, extending ADR 18's "pork appears only in section 1": pork is the food readers ask about, and PSA has its farm price only for a live hog (`Hog for Slaughter`, AFN11), against a kilo of kasim in stores. So pork's chart draws each price as a change from its own 2018 average (`change_only_monthly`, `data.since_2018`), its cards name both products, and it gets no farmer's share or peso gap.
- **Not pesos on one axis:** the space between a live-hog line and a kasim line would read as a gap that the products' difference, not the middle, creates.

## 21. The middle is the story's villain, and amber is its colour
Chosen 2026-11-11 after a critique found the page had no villain, no stakes and the same template five times. The middle (traders between farm and store) is the villain, shown by our data: the typical food's trader's cut grew from 16 to 21 centavos of a peso since 2018. The public record (the PCC's onion cartel ruling of 1 Oct 2026) sits under it as proof that it happens, worded "found" or "alleged" with no person's name, and stays hidden (`views.SHOW_RECORD`) until the owner checks its sources by hand. The page opens on the 2023 onion crisis (store ₱468 against farm ₱216 in January), the ratchet is labelled an example on screen, and a one-line ending closes it. Amber, ADR 19's "what you pay", now marks the middle: the traders' part of the peso, the gap between farm and store, the ratchet's climb. The store price is ink. An ECharts or Altair store series is left uncoloured as the second uncoloured series, so the theme's palette (`chartCategoricalColors[1]`, the text colour) picks the ink in the browser for each mode.
- **Not amber as "what you pay":** the villain needs the one warm colour; a store price is what the reader already knows.
- **Not choosing the ink in Python (`st.context.theme`):** Python learns the theme a rerun late (ADR 19), so the ink would be wrong for a run after a switch.

## 22. Fish joins with a quarterly farm price, set against the quarter's average store price
Chosen 2026-11-11, reversing the earlier choice to leave fish out: bangus, tilapia and galunggong are what readers eat with rice, and PSA prices the same species at the farm (`NFG/0152M4GFPF0`, by quarter, about 4.7 MB a release) and wholesale (`NWSNEW/0052M4AWB10`, monthly). A fish row in `int_farmer_share` is one quarter (`months_in_period` 3, `month` its first month), its farm price against the average of the quarter's three retail and wholesale months, kept only when all three exist. Fish joins every section with a farmer's share, but not the ratchet: four points a year are too coarse to time a 15% move.
- **Not spreading the quarter's price over its months:** that invents monthly farm prices PSA never published.
- **Not a separate fish model:** the farmgate staging reads quarters next to months (`Species` column, `Quarter` periods), so every share test covers fish too.

## 23. The middle section compares farm and store growth since 2018, meat included
Chosen 2026-11-11, replacing ADR 14's "the middle's cut against inflation" on screen: a peso gap needs a farm and store price for the same product, so meat (a live animal against a cut) couldn't appear. Each food's farm and store price growth since 2018 (`growth_since_2018`, the same windows as `food_verdicts`) is a percent for both, so meat sits on the same dumbbell chart as the crops, with inflation as a line. A store price that grew faster than the farm price is the middle growing; diesel, transport and fuel move to the tooltip. `food_verdicts` keeps the verdict for "Check your food".
- **Not the peso gap with meat left out:** meat is what readers ask about first.

_Since 2026-11-21 (owner, at the v4 read) the chart is one bar per food, the points the store grew more than the farm, amber where it did and grey where it didn't. The dumbbell's 50 labels and inflation line read as clutter; each food's prices and its gap against inflation stay in "Check your food"._

## 24. The page is a mystery for a reader who doesn't follow the news, solved by the record and ended with what can be done
_Its one page is replaced by ADR 25's four pages; the mystery order still holds across pages 1 and 2._

Chosen 2026-11-20 after the owner, viewing story v2, found no one to blame, no reason given and no stake for the reader. The reader knows nothing of farm prices and doesn't watch the news, so the page opens on a question they feel and every section moves toward its answer: a newcomer's picture of the chain from farm to store, the middle's share in our data, who regulators caught (the public record, on the page once the owner checks its sources), and a closing section on what is being done and what the reader can do. Amends ADR 14 (the record now answers the story instead of sitting hidden under section 4), ADR 18 (a section may be text only, or carry no chart) and ADR 21 (the villain gets a face from the record). Data numbers stay computed from tested marts. Context text (who traders are, why a middle exists, why farmers are poor, the causes and the fixes) may be written by hand, each fact with a cited source. Blame stays worded "found", "charged" or "alleged", names no private person, and never comes from our prices alone.
- **Not an explainer that names no one:** story v2 was that page, and it gave a newcomer no reason to care.
- **Not causes kept to tooltips:** a newcomer never opens them, and without a cause on screen the gap reads as nobody's doing.
- **Not Filipino or Taglish:** the page stays in plain English (the owner dropped a Filipino version, ADR 26); the video can carry the Taglish voice.

## 25. Four short pages under a top navigation, each section within a word budget
Chosen 2026-11-21 after the owner, reading story v3 top to bottom, found it "very wordy", and because the pipeline, the repo's first point, was out of view. The one page splits into four, in reading order: the story (`/`, the whole finding in about 90 seconds on a phone), who got caught (`/caught`, the proof that it's every food and not new, then the record and what can be done), check your food (`/food`) and how it's built (`/how`, the pipeline drawn with `st.graphviz_chart`, four facts and the repo link). Each page ends with an `st.page_link` to the next. Each section keeps its headline, at most one line under it and one so-what line; detail goes in a tooltip or page 1's closed Sources expander, which holds the citations for page 1's hand-written facts. Replaces ADR 24's one page; its mystery order holds across pages 1 and 2. The README leads with the pipeline.
- **Not a sidebar:** a phone hides it behind a menu. At phone width Streamlit folds the top navigation into a `»` menu too, so each page's "Next →" link is the main way on.
- **Not tabs on one page:** a tab has no URL of its own to share, and every tab's charts would render on load.
- **Not Mermaid:** Streamlit draws none, and Graphviz ships with it.
- **Not the ratchet as a toy:** at the owner's read on 2026-11-21 its buttons went; the chart stays as a still example, three moves up and back.
- **Not new content in the same job:** v4 only cuts and moves, so the owner can judge the split alone.

## 26. The receipt is the reader's own basket, and the story opens on the newest month's move
Chosen 2026-11-21 at the owner's final read of story v4. Page 1, section 3's receipt starts as the example basket (ADR 24's pick) and the reader adds or drops foods in a multiselect; its so-what is computed from that basket: what of its total is spent after the farm, and that times 52 / 12 as a month of weekly shopping. A line under the title names the newest month's biggest whole-centavo move in a farmer's share (`data.newest_move`), so a reader coming back after a PSA release sees what changed. Both are computed on each release, like every headline.
- **Not quantities per food:** a food is one line at its unit (the example's ½ kg of onion and 12 eggs aside), which keeps the widget one tap on a phone.
- **Not share cards or a Filipino version:** both were proposed and dropped by the owner the same day.
