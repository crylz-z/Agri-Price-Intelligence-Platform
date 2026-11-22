# Seasonal baseline: "is this price usual for this month?"
Status: building · created 2026-11-22

## Why
A shopper on "Check your food" sees a price but can't tell whether it is normal for the time of year: a November tomato spike happens most years, but nothing on the page says so. The dashboard never flags single months today. The "suspicious" verdict compares full-year averages (`int_food_verdicts.sql`) and the price changes compare the same month a year earlier (`int_price_changes.sql`), so this is a new answer for the shopper, not a fix for an existing flag.

## Outcome
Under the price chart on "Check your food", a 12-month "usual year" chart. A shaded band shows each month's usual store-price range in today's pesos, and a line shows the last 12 months of store prices. One sentence under it names the food's usual cheapest and dearest months and labels the latest month "usual", "higher than usual for <month>" or "lower than usual for <month>".

## Decisions
- **Reader:** the shopper. Neutral ink only, never the orange used for "suspicious": this is about the season, not about the middle.
- **One chart plus one sentence** stand in for a separate cheapest-month calendar. The sentence carries the cheap and dear months.
- **Source:** national store prices from `int_staple_prices`, not `farmer_share_monthly`. The farmer-share mart drops months with no farm-gate price: red onion has only 6–10 months a year there, but its store price runs every month.
- **Seasonal ratio:** each month's store price divided by that food's average over the same calendar year. Uses full past years only (12 months each), 2018 through the last complete year, never the current year. Dividing by the year's own average removes general inflation.
- **Usual range:** for each food and calendar month, drop the highest and lowest year's ratio and take the min–max of the rest (6 of 8 years today). Caption wording: "the range of past years, leaving out the highest and lowest".
- **Today's pesos:** band = ratio × the average store price over the 12 months *before* the latest month, so the month being judged doesn't set its own band.
- **Minimum history:** a food/month gets a band only with ≥ 5 full past years.
- **Barely seasonal:** when a food's swing (max − min of the median monthly ratio) is under 5%, the sentence says "Its price barely changes with the season." and gives no verdict. Profiled swings: rice 2%, egg 4%; tomato 36%, carrot 31%.
- **Scope:** national only; every food with a national store price (all 28 in `seeds/staples.csv`). Fish is included: only its farm-gate price is quarterly; its store price is monthly. No regions.
- **Tests:**
  - dbt: each food-year's ratios average to 1; `usual_low ≤ usual_median ≤ usual_high`; `(staple, calendar_month)` unique; ≤ 12 rows per food; `years_used ≥ 5`.
  - pytest: the sentence function (within / above / below / barely-seasonal / no band).

## Free calls
- Model and column names, and whether the last-12-months prices sit in the mart or come from a second query.
- How the chart orders its x-axis (calendar Jan–Dec, or the 12 months ending at the latest month).
- Chart styling, within `.claude/rules/dashboard.md` and the existing `food_chart` palette.
- Fixture shape for tests, within `.claude/rules/tests.md`.

## Checklist
- [x] `int_seasonal_index` and mart `seasonal_baseline` (one row per food × calendar month: usual low/median/high in today's pesos, years used, swing) — done when `dbt build --select +seasonal_baseline` passes against the local lake (`--vars "{lake_root: 'E:/Workspace/apip/tmp/lake'}"`) with the five dbt tests above, and a query shows Tomato's November median above its April median and Well-milled rice's swing under 0.05.
- [x] Pure functions in `src/dashboard/data.py` for the chart rows and the sentence — done when the new pytest cases pass offline (`uv run python -m pytest`).
- [ ] The "usual year" chart and sentence on "Check your food", for both share foods and change-only foods (meats) — done when http://localhost:8503 shows the band and sentence for Tomato, Red onion and Pork kasim, the barely-seasonal sentence for Well-milled rice, and the barely-seasonal sentence for Bangus. Screenshots judged by `screenshot-checker` at phone and wide widths.
- [ ] Mention it where the dashboard explains its methods (`how.py`), in one plain paragraph that includes the trimming and the 5-year minimum — done when the page renders and `test_pages.py` passes.
- [ ] Caption: replace `tmp/linkedin/caption.md:46` with "Next: a 'usual for this month' range on each food, so a normal November spike reads differently from an unusual one." — done when the body recount (`awk '/^---$/{n++; next} n==1' tmp/linkedin/caption.md | wc -m`) stays ≤ 3,000. If the feature ships before posting, move it into the body as current instead.
- [ ] Backlog: add "Who keeps the harvest drop: rice's farm price swings 10% with the season, its store price 2%, and the gap 20% (rice keeps in storage, so a flat store price alone proves nothing)" under Ideas — done when the line is in `.plans/backlog.md`.
- [ ] Full check — done when `uv run python -m pre_commit run --all-files` and `uv run python -m pytest` pass.

## Review
- Does the band and sentence read correctly for tomato, onion, rice and pork on a phone?
- Is the wording plain and free of any claim the data doesn't back?

## Reference
- Profile behind the swings (2018–2025 full years, local lake, national): store swing tomato 0.36, carrot 0.31, repolyo 0.25, calamansi 0.25, talong 0.24, potato 0.15, egg 0.04, well-milled rice 0.02; most vegetables dearest in Nov–Dec and cheapest in Apr–May. The local lake differs slightly from the test fixtures and from R2.

## Log
- Fish included: the "quarterly" premise held for farm-gate prices only; retail fish prices are monthly, so they get a baseline like any food (all three swing ~3%, so they read as barely seasonal).
- Tests sit on a new table `int_seasonal_baseline`, with the mart a `select *`: the pipeline rule says external marts are written before their own tests run.
- Column `price_level`, not `level`: `level` is a DuckDB keyword.
- The peso level is null unless all 12 months before the latest have a price, so a food with a gap shows no band rather than a skewed one.
