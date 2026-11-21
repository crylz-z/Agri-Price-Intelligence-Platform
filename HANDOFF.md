# Handoff

## Next action
Story v5 is planned in `.plans/story-v5/plan.md` (from a grilling with the owner on 2026-11-21): the short-version page, the hook fix, chapter labels and the dumbbell. Run `/build story-v5` when the owner says so. Before that, the owner may commit v4 and the rig realignment: commit **only what they approve** (staged by explicit paths, no Claude credit). The local page runs on http://localhost:8503 (started in the background by the previous session). After that, each step only when the owner says so: push `restructure`, open a PR to `main`, merge, and let the scheduled pipeline rebuild R2 (it adds the fish snapshots and `growth_since_2018`).

## State on disk (branch `restructure`, not pushed)
- Story v3 is committed (`3b64c2e`, `0447e50`). All of v4 is uncommitted, signed off by the owner: `src/dashboard/{app,views,data,nav,how}.py`, `src/dashboard/app_pages/` (intent-to-add, like `nav.py` and `how.py`), `tests/test_pages.py`, `tests/test_dashboard_data.py`, the fixture `tests/fixtures/marts/farmer_share_monthly.parquet`, `dbt/seeds/farmer_share_exclusions.csv`, `dbt/dbt_project.yml`, `dbt/seeds/_seeds.yml`, `dbt/models/intermediate/int_farmer_share.sql`, `dbt/tests/assert_farmer_share_recompute.sql`, and the docs (`docs/adr.md` ADRs 23, 25 and 26, `GLOSSARY.md`, README). The deletion of `.plans/story-v3/` is staged. No plan is open.
- Rig realignment (2026-11-21, `/harness:rig audit`, owner approved every row), also uncommitted:
  - The project now uses the harness flow, `/grill-with-docs` → `/to-plan` → `/build` (`CLAUDE.md` Workflow). The skills `to-spec`, `to-tickets` and `implement` are deleted (staged). `research` stays in `.claude/skills/`: the owner wants nothing added to the harness repo.
  - `grill-with-docs` now calls `harness:grilling`. The old target, `anthropic-skills:grilling`, is switched off globally.
  - `handoff.md` became `HANDOFF.md` (staged rename), the name auto-handoff writes.
  - The local-run notes moved from this file into `.claude/rules/dashboard.md` → Local run. Lines that repeated `CLAUDE.md` were cut from the rules.
  - A Stop hook, `.claude/settings.json` → `scripts/stop_gate.py`, runs pytest and pre-commit when the tree differs from HEAD and from the last green run (stamp `.claude/stop-gate.stamp`, gitignored). It is proven: a deliberate failing test blocked with exit 2, and the fix let the stop through.
- `pytest` (109), `pre_commit run --all-files` and a local `dbt build` (99 pass, 1 warning, the known farmer-share-above-one warning) passed on 2026-11-21. Screenshots at 1440 and 375 px, light and dark, passed.

## Story v4's last changes (after the owner's final read)
- **Pechay:** PSA's national farm price for Jan–Mar 2026 (₱9.58, ₱15.10, ₱83) has no support in its regional prices, so `farmer_share_exclusions.csv` has an optional `month` column (blank means every month) that excludes those three months. Pechay now has 4 falling months, below `MIN_MOVE_MONTHS`, so it drops out of the ratchet's foods on live data. The test fixtures are an older build: only the three rows were removed from the farmer-share fixture.
- **Shorter headline:** "Traders now take X centavos, up from Y", so its (?) stays on the headline's last line.
- **Your basket (ADR 26):** page 1's receipt has a multiselect that starts as the example basket (`data.BASKET`); the reader can pick any food with all three prices (`data.basket_choices`).
- **Newest move (ADR 26):** one line under the title gives the newest month's biggest whole-centavo move in a farmer's share (`data.newest_move`, `views.newest_line`).
- The owner dropped the share cards and the Filipino version (ADR 26).

## Open to the owner
- Page 2's record order: rulings first (the spec), or by date.
- Whether to delete the old R2 marts (on the backlog).
- On the local lake the newest month (Oct 2026) has only 2 foods (both rice), so the line reads "regular rice … 66 to 68". It updates on each PSA release.

## Environment
- Local page, lake and screenshots: `.claude/rules/dashboard.md` → Local run.
