# Backlog

Work not yet specced. When an item is picked up, `/grill-with-docs` it, then `/to-spec` it into `.plans/<slug>/`, and delete its line here.

## Before going public
- Check pechay's 2026 farm price dip to about ₱10.
- Ask the owner about deleting the old R2 marts (listed in `.claude/rules/pipeline.md`).
- R2 lacks the fish snapshots and the `growth_since_2018` mart until `restructure` merges and the pipeline runs; until then the page runs only from the local lake (`tmp/local_app.py`).

## After story v3
- The video, then push and PR, when the owner asks.
- A Filipino version of the page.

## Ideas
- CPI for the bottom 30% of households (`PI/BIH/2018NEW`).
- A household's monthly cost to the middle, from PSA family spending (FIES).

## Dev harness
- The local lake now lives in `tmp/lake/` (gitignored), filled by `tmp/fetch_lake.py` from PSA and built with dbt's `lake_root` var; `tmp/local_app.py` serves the page from it. Helpers worth keeping could move to `scripts/`.
- dbt's profile is `:memory:`, so intermediate models can't be queried after a build; the workaround is running the compiled SQL from `dbt/target/compiled/` in DuckDB.
