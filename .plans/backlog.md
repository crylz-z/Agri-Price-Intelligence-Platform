# Backlog

Work not yet planned. When an item is picked up, plan it in `.plans/<slug>/` and delete its line here.

## After story v3
- The video, then push and PR, when the owner asks.

## Ideas
- CPI for the bottom 30% of households (`PI/BIH/2018NEW`).
- A household's monthly cost to the middle, from PSA family spending (FIES).
- "Who's responsible?" in the short version, for the general public: what's proven (the PCC onion cartel ruling, moved up), what's suggested (up fast, down slow; the middle's part growing despite the 2015 and 2024 laws), what's not proven (how much is cost and how much is profit, and whether enforcement is enough). Every government claim needs a cited source (ADR 24).
- Imports: the lake has no import data (only PSA retail, wholesale, farm-gate prices and CPI). Checked 2026-11-22, estimated 2–3 days. The source is PSA OpenSTAT `2L/IMT/GKI` (monthly gross kilos imported, by 11-digit HS code × 217 countries, national only, one table per year). It uses the same PXWeb API as `ingest.py`, but the API can't filter by commodity: a single month is ~65 MB and takes ~65 s, and a whole year times out. So ingest has to filter to food HS codes before saving, which breaks the "snapshots stored as returned" rule (needs an ADR). It also needs an HS-code→food seed (the table carries codes only, so labels come from the AHTN tariff list). Data has `..` cells and preliminary `P` months, and old years get revised (2019 updated 2026-10-28). BPI publishes no onion SPS-IC series: PhilRice Ricelytics has rice SPS-IC counts only up to Jan 2025.
