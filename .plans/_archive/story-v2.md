# Plan: story v2, a villain, meat and fish (session 30 draft)

Status: answered "yes to all" and built in session 31 (uncommitted).

## Why (session 30 critique)
The page is honest and clean, but it's a lecture, not a story:
1. **No villain.** The public record (`suspects.csv`) is hidden, so the page shows a pattern with no actor. Traders, the strongest finding (16 → 21 centavos of every peso), are a grey bar segment and one so-what line.
2. **No stakes.** Centavos and percents, nothing a reader feels in pesos.
3. **The same template five times:** big number → headline → sentence → chart → lightbulb, with three similar horizontal bar charts.
4. **A weak opener and the best data unused.** Section 1 leads with tomato. The onion crisis (Jan 2023: farm ₱216, wholesale ₱393, store ₱468; Mar 2023: farm ₱65, store ₱220) isn't on the page.
5. **Only crops.** 18 foods: 13 vegetables and spices, monggo, 2 rices, egg. No meat or fish, and those are what a reader eats with rice.
6. **Section 3's chart is an example, not data.** Only the (?) tooltip says so.
7. **No ending.** The page stops on a food picker.

## Data facts checked (2026-11-09)
- **Fish, same product at both ends.** PSA `NFG/0152M4GFPF0` (Fisheries: Farmgate Price by Geolocation, Species, Year and Quarter) is quarterly, 2002 to Q3 2026, about 4.7 MB per release. Species match the retail items: Milkfish, Tilapia, Roundscad (Galunggong). Wholesale `NWSNEW/0052M4AWB10` (Fish) is monthly with Bangus, Tilapia, Galunggong.
  - National Q3 2026 farm against Jul–Sep 2026 average store: bangus ₱142 / ₱241 (59¢), tilapia ₱104 / ₱183 (57¢), galunggong ₱128 / ₱237 (54¢).
  - 2018: bangus 103 / 163, tilapia 76 / 128, galunggong 68 / 143. The gap grew about +63%, +51% and +46%, all past inflation (+33%).
  - Q3 2025 → Q3 2026: bangus farm −2%, store +4%; tilapia farm +4%, store +2%; galunggong farm +5%, store +7%.
- **Meat, different products.** The farm price is per kg live weight (AFN11 `Hog for Slaughter`, `Broiler Chicken`, `Cattle for Slaughter`, already ingested), and the store price is per kg of a cut. PSA has no live-to-cut factor, and no wholesale meat table. Sep 2025 → Sep 2026: hog −19% (kasim −10%, liempo −9%), broiler −3% (whole chicken −1%), cattle −5% (beef with bones +2%).
  - A ratio of percent changes is fair if the yield stays constant; pesos side by side are not.
- **Onion check:** Dec 2022 farm ₱335 sits above store ₱307, and Aug–Nov 2022 have no farm price. Check before the hook uses Dec 2022; start the hook at Jan 2023.

## Questions (the user's answers go here)
1. Villain = **the middle** (traders between farm and market), shown by our data, with the record as proof that it happens (PCC's onion cartel ruling, 1 Oct 2026). "Found" and "alleged" wording, no person's name. **(rec)** The user checks the PCC source by hand first.
2. Open with the **onion crisis** as a real-data hook: farm, wholesale and store lines, Jan–Mar 2023. **(rec)**
3. Colour: **amber becomes the middle** (traders' part, the gap); the shopper's store price turns ink; the farmer stays blue. **(rec)** The alternative keeps amber as "what you pay".
4. Fish: ingest both tables; bangus, tilapia and galunggong join sections 1, 2 and 4 and "Check your food", but not the ratchet (quarterly is too coarse). **(rec)**
5. Meat (kasim, liempo, whole chicken, beef): section 1 and "Check your food" as percent-only, and section 4 becomes **"farm price grew X%, store price grew Y% since 2018"**, one dumbbell per food with an inflation line, so meat sits in the same chart. **(rec)** The alternative keeps the peso gap against inflation and leaves meat out of section 4.
6. Shape: hook → this year → your peso → the villain (traders grew, + the record) → the ratchet (labelled "example" on screen) → check your food → a one-line ending. **(rec)**

## Build steps (after the answers)
1. **Data:** ingest the fish farmgate and wholesale tables (`ingest.py`, seeds, staging); quarterly fish rows in the marts; meat seed rows in `change_only_commodities.csv`. Done when `dbt build` on the local lake reproduces the fish numbers above and the tests pass.
2. **Marts:** section 4's percent growth for every food (`food_verdicts` or a new mart), the onion hook series. Done when the fixtures are refreshed and the page-test pins are updated.
3. **Page:** the new section order, the villain colour and the record section (sources checked). Done when the screenshots at 1440 and 375 in both themes pass the 30-second test: after one scroll the user can say the hook, the villain and the mechanism.
4. **Docs:** ADRs (villain, fish, section 4 metric), the GLOSSARY section table, the rules colour line, README. Done when no doc describes the old order.
