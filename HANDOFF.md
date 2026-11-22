# Handoff

## Next action
Nothing is open. Story v5 shipped to `main` on 2026-11-22. The next scheduled pipeline run ingests the new fish snapshots, which triggers `dbt build` and writes `growth_since_2018` to R2. After that, the live dashboard matches the local one. Check that run in GitHub Actions. If it fails, fix it, then rerun "Daily PSA Prices" by hand with **build** ticked. Next work comes from `.plans/backlog.md` when the owner picks it.

## State
- The last full check passed: 116 tests and pre-commit. The betterleaks scan of the whole history found no leaks.
- Checks run in two places only: `pre-commit` at each commit (ruff, mypy, betterleaks for secrets; under 3 s) and CI on push and PR (the same hooks, `pytest`, `dbt parse`). There is no per-edit or turn-end hook.

## Open to the owner
- Whether to delete the old R2 marts (on the backlog).

## Known pipeline gaps (accepted 2026-11-22)
- A failed `dbt build` isn't retried: the next day ingest finds nothing new and skips dbt. Rerun by hand with **build** ticked.
- GitHub turns off a public repo's schedule after 60 days with no commits. It emails first.
- Scheduled runs start hours after the 02:00 UTC cron, around 17:00 PHT.

## Environment
- Local page, lake and screenshots: `.claude/rules/dashboard.md` → Local run.
- The terminal is cp1252, so a `print` of "₱" inside pytest fails. Don't print from tests.
