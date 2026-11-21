# 09 Docs and the owner's read-through

Status: done
Spec: Verification
Blocked by: 08

README's story description, `GLOSSARY.md` → Section, and the dashboard rules match the built page; screenshots pass at 1440 and 375 px, light and dark.

Done when:
- [x] `uv run python -m pytest` and `uv run python -m pre_commit run --all-files` pass.
- [x] Review: the owner read the page top to bottom (2026-11-21): "not bad", but too wordy for one page.

## Notes
- 2026-11-21: docs checked against the built page (headers from `test_the_headlines_tell_the_story_in_order`). README's dashboard bullet still told story v2 (7 sections, suspects off the page); it now lists the 9 v3 sections. GLOSSARY → Page said `?food=` picks section 6; it is section 8. The glossary's section table and `.claude/rules/dashboard.md` already matched.
- Started while 08's owner review was pending, at the owner's request; the read-through covers both.
- pytest (83) and pre-commit pass. Screenshots at 1440 and 375 px, light and dark, from `tmp/local_app.py`: no exceptions, no horizontal scroll, no cut-off text.
- For the read-through: on the local lake, section 3's big number says traders get 21¢ (latest month) and section 4's headline says 20 centavos "now" (last 12 months). Both are correct, but a reader may see them as a contradiction.
- Owner, 2026-11-21: the page is fine, but the tooltips are too wordy and after the hook it reads like an article. Done: section 3 dropped its traders' big number and its so-what no longer splits the 54 centavos, so traders' part shows only in section 4. The four headline tooltips went from 5–8 lines to one line plus two or three short bullets. The rule is in `.claude/rules/dashboard.md`. For engagement past the hook, the owner picked one of four ideas, the ratchet toy, and asked that it engage without repeating the text. It is built here (spec → Engagement): `ratchet_toy` is an `st.fragment` with three buttons, `data.ratchet` takes the presses instead of `swings`, `views.SWINGS` is gone, and `test_the_reader_plays_the_ratchet` presses it. Checked in Edge at 1440 light and 375 dark, both empty and after 5 presses.
- Gotcha: an ECharts `endLabel` whose formatter is "" falls back to the raw value, so the empty toy hides its end labels with `show`.
- Owner, 2026-11-21, final read: the whole page is fine but too wordy, and the story had pushed the pipeline (the repo's first point) out of view. Agreed next: story v4, split into pages and cut words (backlog → After story v3).
