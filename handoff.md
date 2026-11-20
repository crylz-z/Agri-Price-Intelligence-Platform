# Handoff

## Next action
Resume from `.plans/backlog.md` → "Ship story v2". First ask the owner to look at the page (run it from the local lake, below) and say whether to commit. Commit only when they say so.

## State on disk (branch `restructure`, not pushed)
- Last commit `26f3521` (2026-11-18): skills and `.plans/` are tracked; the ticket workflow is in `CLAUDE.md` → Workflow.
- Uncommitted:
  - the story v2 build, about 43 files across ingest, seeds, dbt models and tests, fixtures, `views.py`, `data.py`, page tests and docs;
  - `.gitignore` (stops ignoring `handoff.md`) and this file. Commit these on their own: `chore: track handoff.md`.

## Steps left
1. The owner reviews the page; then commit story v2 in the three parts the backlog lists (data, page, docs).
2. The video, then push and PR, after the owner asks.
3. The backlog's "Before going public" items: suspect sources, pechay's dip, old R2 marts.
4. Any new piece of work: `/grill-with-docs` → `/to-spec` → `/to-tickets` → `/implement`, one ticket per session.

## Open to the owner
- Whether the page is ready to commit.
- Whether to delete the old R2 marts.

## Environment
- Workflow skills live in `.claude/skills/` (tracked): `grill-with-docs`, `to-spec`, `to-tickets`, `implement` (`<slug> all` runs tickets in parallel worktrees; see its `PARALLEL.md`). `grilling` and `writing-for-agents` come from the owner's synced global skills, not the repo.
- `developing-with-streamlit` is Streamlit's official meta-skill: it runs `scripts/discover.py --project-dir <repo>` and reads the docs bundled with the installed Streamlit. Bare `python` isn't on PATH here; use `uv run python`.
- Subagents default to Sonnet (`CLAUDE_CODE_SUBAGENT_MODEL` in the owner's user settings); the main session is Opus.

## Local dev setup (owner's Windows PC only)
These live in Claude Code's session scratchpads under `%TEMP%\claude\`. On any other machine they don't exist: build the lake as the README's local build describes. R2 lacks the fish snapshots and `growth_since_2018` until story v2 merges, so the page needs the local lake.
- Lake: `%TEMP%/claude/bd704905e90687f0/f76f9f49-f028-45e4-b8c7-0dfe16a97bec/scratchpad/lake/`
- `local_app.py` (the page from the lake, port 8503): `%TEMP%/claude/25eba87c7383c115/47b95f7f-d7fa-48c9-b134-34d7bf850efe/scratchpad/local_app.py`
- Session 31's helpers (`fixtures.py`, `render.py`, `crop.py`, `q.py`, `edit.py`): `%TEMP%/claude/25eba87c7383c115/309e03af-bd9c-40b5-a63a-2991a52748cf/scratchpad/`
- Server: `uv run python -m streamlit run <local_app.py> --server.port 8503 --server.headless true`. Screenshots: the `scripts/screenshot.py` docstring, with `APP=<local_app.py>`.
