# Handoff

## Next action
Story v3 is done (all 9 tickets). Start story v4 with `/grill-with-docs`, from the draft in `.plans/backlog.md` → After story v3. Before that, offer the owner the two commits below and `/code-review`. Once v3 is committed, delete `.plans/story-v3/` (git history keeps it).

## State on disk (branch `restructure`, not pushed)
- Story v2 is committed (up to `6b40d64`). Story v3 is not. Commit only when the owner asks. Suggested split:
  - `docs: story v3 spec, tickets and ADR 24`: `docs/adr.md`, `GLOSSARY.md`, `.claude/rules/dashboard.md`, `.plans/`, `CLAUDE.md`, `README.md`, `handoff.md`, and the other doc edits in `git status`.
  - `feat(dashboard): story v3`: `src/dashboard/`, `dbt/seeds/suspects.csv`, `dbt/seeds/_seeds.yml`, `tests/`.
- `pytest` (85) and `pre_commit run --all-files` passed on 2026-11-21.

## Open to the owner
- Section 6's order: rulings first (the spec), or by date.
- A your-own-basket receipt: proposed, not specced.
- Whether to delete the old R2 marts (on the backlog).

## Environment
- Use `uv run python`, since bare `python` isn't on PATH.
- Local page: `uv run python -m streamlit run tmp/local_app.py --server.port 8503`. It reads from `tmp/lake/` (gitignored). Refill it with `uv run python -m tmp.fetch_lake`, then build with `--vars "{lake_root: 'E:/Workspace/apip/tmp/lake'}"`. **Restart the server after editing `src/dashboard/`**, or it serves the old `views.py`.
- Screenshots: `scripts/screenshot.py` (usage in its docstring). Set `CHROME` to Edge, `APP=tmp/local_app.py`, `SHOT_DIR=tmp/shots`, and both `STREAMLIT_THEME_*FONT=sans-serif`. The script can't click, and its shots are full-page, so crop them with `uv run --no-project --with pillow`.
- In bash heredocs fed to Python, a `\n` inside a string literal becomes a real newline. Write those lines with Edit.
