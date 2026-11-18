# Backlog

Work not yet specced. When an item is picked up, `/grill-with-docs` it, then `/to-spec` it into `.plans/<slug>/`, and delete its line here.

## Ship story v2
Story v2 (`_archive/story-v2.md`) is built but not committed on branch `restructure`. First have the owner look at the page and decide whether to commit. Suggested commits: (1) data: ingest, seeds, dbt models and tests, fixtures; (2) page: `views.py`, `data.py`, page tests; (3) docs. Then the video, then push and PR.
- R2 lacks the fish snapshots and the `growth_since_2018` mart until the merge; until then the page runs only from a local lake build (`--vars "{lake_root: '<lake>'}"`, as in the README).
- The scroll-motion check was not rerun after the redesign; its key is now `.st-key-reveal_middle`.

## Before going public
- The owner checks the suspect sources by hand (`_archive/story-rethink.md` → "Step 1 results"), then turns the record on (`views.SHOW_RECORD`).
- Check pechay's 2026 farm price dip to about ₱10.
- Ask the owner about deleting the old R2 marts (listed in `.claude/rules/pipeline.md`).

## Ideas
- CPI for the bottom 30% of households (`PI/BIH/2018NEW`).

## Dev harness
Leftovers from the harness session (2026-11-18):
- The local lake, `local_app.py` and session helpers live in throwaway temp folders. Give them a stable home: helpers worth keeping (fixture refresh, offline render, screenshot crop) go in `scripts/`; the lake goes in a gitignored folder.
- dbt's profile is `:memory:`, so intermediate models can't be queried after a build; the workaround is running the compiled SQL from `dbt/target/compiled/` in DuckDB.
