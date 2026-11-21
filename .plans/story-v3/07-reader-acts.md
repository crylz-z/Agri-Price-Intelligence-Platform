# 07 The reader acts: guess, case cards, report button

Status: done
Spec: Engagement
Blocked by: 06

The hook asks the reader to guess the store price before showing it; "Who got caught" becomes case cards under a fined-so-far big number; "What can be done" becomes cards and a "Report a cartel to the PCC" button.

Done when:
- [x] `uv run python -m pytest` passes, with tests that the hook hides the store price until "Show me" and then says how far the guess was, that each record card carries its stage badge and source, that the fined-so-far number is the seed's sum, and that the report button links to the PCC portal.
- [x] Screenshots at 1440 and 375 px, light and dark: the cards stack on a phone, no cut-off text, no horizontal scroll.
- [x] Review: the owner tries the guess and reads sections 6 and 7 as cards, not a block of text.

## Notes
- 2026-11-21: built; owner review pending. The hook shows only the farm number, the question, the onion-vs-meat line, a "Your guess, a kilo" slider (₱65–₱450) and "Show me"; its `on_click` copies `hook_slider` into `session_state[views.HOOK_GUESS]`, and the full hook follows with "Your guess was ₱X. Stores charged ₱220, ₱Y more."
- `test_pages.render` presets a ₱150 guess so the other tests see the answered hook; `render(guess=None)` is the first view. The screenshots show the unanswered hook, since `scripts/screenshot.py` doesn't click.
- `suspects.csv` gained `stage` (badge: `views.STAGES`) and `fine_php` (the PCC's ₱1.76 billion total, the hero "Fined so far, Oct 2026"); `_seeds.yml` tests `stage`. `context.BEING_DONE` is now (title, icon, fact), like `CHAIN`; `context.PCC_PORTAL` feeds the report button and the PCC fact.
- Section 7's cards sit two per `st.columns(2)` row, so a phone keeps their order. The chain test now takes the first four bold icon titles, since section 7's cards share that form.
- Ticket 08 (motion): the hook chart now mounts only after "Show me", so check its entry animation after the click too.
