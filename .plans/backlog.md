# Backlog

Work not yet planned. When an item is picked up, `/grill-with-docs` it, then `/to-plan` it into `.plans/<slug>/`, and delete its line here.

## Before going public
- Ask the owner about deleting the old R2 marts (listed in `.claude/rules/pipeline.md`).
- R2 lacks the fish snapshots and the `growth_since_2018` mart until `restructure` merges and the pipeline runs; until then the page runs only from the local lake (`tmp/local_app.py`).

## After story v3
- The video, then push and PR, when the owner asks.

## Ideas
- CPI for the bottom 30% of households (`PI/BIH/2018NEW`).
- A household's monthly cost to the middle, from PSA family spending (FIES).
- "Who's responsible?" in the short version, for the general public: what's proven (the PCC onion cartel ruling, moved up), what's suggested (up fast, down slow; the middle's part growing despite the 2015 and 2024 laws), what's not proven (how much is cost and how much is profit, and whether enforcement is enough). Every government claim needs a cited source (ADR 24).
- Imports: the lake has no import data (only PSA retail, wholesale, farm-gate prices and CPI). Import volumes and timing (for example, onion import permits during the 2022–23 crisis) would need a new source.

## Dev harness
- The local lake now lives in `tmp/lake/` (gitignored), filled by `tmp/fetch_lake.py` from PSA and built with dbt's `lake_root` var; `tmp/local_app.py` serves the page from it. Helpers worth keeping could move to `scripts/`.
- dbt's profile is `:memory:`, so intermediate models can't be queried after a build; the workaround is running the compiled SQL from `dbt/target/compiled/` in DuckDB.
