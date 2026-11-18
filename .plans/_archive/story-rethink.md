# Spec: the case file (ADR 14)

Status: agreed 2026-11-08 (session 21); step 1 done in session 22.

**Superseded on page structure (session 24):** the site is 1 page, not 2 (ADR 14, `GLOSSARY.md` → Section). Section 2 is the pass-through (ADR 15). The unused marts, `recipes.csv`, `wage_orders.csv` and `policy_events.csv` are dropped. The data and sources below still hold. Replaces page 1 of `.plans/farm-to-retail-spec.md`; that spec's step 5 (ship) waits until this is built. Terms: `GLOSSARY.md` → Middle's cut, Suspect, Verdict.

## The story
**"Who's eating the farmer's peso?"** Farm prices fell or barely moved, store prices rose, and the pesos in between grew faster than inflation. Our data is the crime scene; the public record names the suspects; one suspect is cleared; the reader then checks their own food.

The user accepted the recommended defaults: the case-file story, 2 pages, blame only from the record with no private individuals named, and inflation (CPI) as the yardstick. Confirm at the start of the build.

## Page 1: "Who's eating the farmer's peso?" (`/`)
Each scroll-stop is one bold computed headline, one big number and one chart; no picker before the payoff; national data only. One colour per actor on every chart: farmer, middle, shopper.
1. **The crime.** Headline from the staple whose farm price fell most while its store price rose (today: red onion, farm −17%, store +48% since 2018). Chart: all 18 staples, 2018 → last 12 months, farm and store (dumbbell or slope); suspicious staples in the alarm colour.
2. **Suspect 1: the onion cartel.** Our evidence: Jan 2023 farm ₱216 vs store ₱468. Record: House agriculture committee (May 2023) found a cartel controlled cold storage and the shortage was artificial; PCC charged 12 onion traders and importers for price-fixing 2019–2023, ₱2.42B penalties recommended.
3. **Suspect 2: rice importers and traders.** Our evidence: after the Jul 2024 tariff cut, palay as milled −37%, store −21%, middle's cut ₱11.5 → ₱15.5 (Jun 2024 → Sep 2025). Record: House probe on importer collusion; Federation of Free Farmers and ex-DA Sec Montemayor say savings went to importers; UP paper "Tariff cuts without consumer gains?" (Trinidad, Ravago, Balisacan 2025). Government policies as dashed markers = the accomplice.
4. **The alibi: repolyo.** Middle's cut grew +36%, the same as inflation; the record points to the chain (7–8 middlemen layers, 16–40% of vegetables spoil, idle cold storage in Benguet).
5. **Your turn:** link to page 2.

Wording rule: on screen only "found", "charged", "alleged", each with its source link; agencies and findings, never a private person's name.

## Page 2: "Check your food" (`/food`, `?staple=`)
Pick a staple → its verdict chip (suspicious / cleared), its ₱100 split (farmer | middle), 2018 → now for farm, store and the middle's cut against inflation, its price history with policy markers, and its suspects with sources if any. Replaces Overview, Compare places and Look up a food.

## Data
- **CPI:** PSA's all-items CPI (2018=100), monthly, national. First look for it on OpenSTAT (the CPI 2018 folder under `DB/2M/PI/`) and ingest it like the retail tables, so it updates itself; fall back to a hand-kept seed only if no table fits. Headline was ~135.6 in Jul 2026.
- **Suspects seed** `dbt/seeds/suspects.csv`: staple, suspect, claim (one line, as the source words it), source name, source URL, date. Hand-kept, rarely changes.
- **Mart** `food_verdicts`: one row per staple, national: farm, store and middle's cut averaged over 2018 and over the last 12 months, CPI growth over the same span, crash pass-through (in months with farm price >15% below a year earlier, average store change ÷ average farm change), verdict.
- **Verdict rule:** suspicious when the middle's cut grew faster than CPI. Settle a margin in step 1 against the numbers below (sayote +43% and repolyo +36% sit next to CPI +36%); the pass-through is shown as evidence, not used in the verdict, because it would flag repolyo too.
- Regional farmer's share and dish wage share leave the dashboard. Their marts and seeds stay until step 4 decides.

## Numbers to reproduce (national, 2018 average vs Oct 2025–Sep 2026 average)
| Staple | Farm | Store | Middle's cut ₱ | Middle grew |
|---|---|---|---|---|
| Ginger | +42% | +103% | 31 → 89 | +191% |
| Sitaw | +76% | +96% | 24 → 53 | +121% |
| Red onion | −17% | +48% | 62 → 125 | +102% |
| Potato | +32% | +67% | 46 → 89 | +95% |
| Kangkong | +133% | +113% | 16 → 31 | +93% |
| Carrot | +38% | +64% | 55 → 99 | +81% |
| Repolyo | −11% | +20% | 53 → 72 | +36% |
| Kalabasa | +71% | +51% | 20 → 27 | +34% |
| Regular rice | +4% | +8% | 12 → 14 | +19% |

Use these as the hand-worked fixture answers in `tests/test_dashboard_data.py` and a dbt recompute test (ADR 11).

## Step 1 results (session 22)
- CPI ingested from OpenSTAT `0012M4ACP22` (national, all items only). Inflation over 2018 → Oct 2025–Sep 2026 is **+33.4%**, not +36%.
- **Margin: 5 points**, chosen by the user. Cleared: Repolyo (+35.8%), Kalabasa (+34.4%), both rices. Sayote (+42.9%) is suspicious. 14 suspicious, 4 cleared.
- **Rice:** cleared over 2018 → now. Page 2 says "cleared since 2018" and still lists the record's tariff-cut allegations beneath (user's choice). Page 1's suspect 2 uses the post-tariff window as planned.
- **Onion case moved on:** PCC decided on 1 Oct 2026 and fined six firms a record ₱1.76B for splitting the onion import market 2019–2023. Some asked for reconsideration. That replaces "charged 12, ₱2.42B recommended".
- `suspects.csv` has 5 rows. These sources were blocked for automated fetch and remain unverified: the PTV, PIDS/FFF and FEF pages, the UP/Ateneo paper's findings, Philstar's 7–8 middlemen layers, and MB 2018 spoilage. Repolyo's alibi cites a 2019 JESAM Benguet study instead (about 42% spoils). Check by hand before page 1 uses them.

## Build steps
1. **Data:** CPI ingest (or seed), `suspects.csv`, `food_verdicts` mart with dbt tests; fixture parquet in `tests/fixtures/marts/`. Done when `dbt build` on the local lake reproduces the table above and the verdict margin is chosen with the user.
2. **Page 1** in `views.py`, `data.py` helpers with tests. Done when every headline is computed and screenshots at 1440 and 375 px in both themes pass the 30-second test: the user can say the crime, two suspects and the alibi after one scroll.
3. **Page 2**; remove the 3 old pages and their tests from `app.py`, `views.py`, `tests/test_pages.py`. Done when pytest and pre-commit are green.
4. **Docs and cleanup:** `GLOSSARY.md` Page and Card tables, `README.md`, `.claude/rules/dashboard.md` (4 pages → 2, the wording rule for suspects); drop marts nothing reads, with the user's OK. Done when no doc names a removed page.
5. **Ship:** commit when the user asks, then `farm-to-retail-spec.md` step 5 (push, PR, rename, merge, redeploy, check the first daily run).

## Sources (record behind the suspects)
- Manila Bulletin 2023-05-17, Quimbo on the onion cartel: https://mb.com.ph/2023/5/17/quimbo-puts-faces-on-alleged-onion-cartel-as-house-ends-probe
- Inquirer, House panel on the onion cartel: https://newsinfo.inquirer.net/1771237/house-panel-blacklisted-trader-runs-onion-cartel/amp
- Journal News price watch (PCC charges, ₱2.42B): https://journalnews.com.ph/price-watch/ (verify on pcc.gov.ph before use)
- PTV, House on rice collusion: https://ptvnews.ph/lawmakers-lament-collusion-to-manipulate-rice-prices-despite-reduced-tariffs-oversupply/
- PIDS, FFF on traders capturing the tariff cut: https://pids.gov.ph/details/news/in-the-news/rice-traders-capturing-benefits-of-low-tariffs-fff
- DZRH, Montemayor: https://dzrh.com.ph/post/tariff-cut-benefited-importers-not-consumers-former-da-sec-montemayor
- UP PRE paper: https://pre.econ.upd.edu.ph/index.php/pre/article/view/1084
- FEF, the other side (retail −7.5% by Feb 2025): https://fef.org.ph/?p=9174
- Philstar 2024-05, 7–8 middlemen layers: https://philstar.com/headlines/2024/05/03/2352191/traders-middlemen-blamed-soaring-commodity-prices
- Manila Bulletin 2018, logistics and spoilage: https://mb.com.ph/2018/02/15/agricultural-logistics-in-the-philippines
- PSA, farm-to-retail gap is PSA's own metric: https://psa.gov.ph/system/files/main-publication/AFIS-Prices-and-Marketing_2019-2023_SIGNED.pdf

Check each case's current status (dismissed, pending, decided) before it goes on screen; the press is from 2023–2025.
