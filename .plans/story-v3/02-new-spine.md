# 02 The new spine: onion question first, section 2 cut

Status: done
Spec: Sections (1, and the cut of story v2's section 2); Verification
Blocked by: none

`case_page` runs in the new order with the sections that exist: the hook, re-asked as March 2023's question (farm ₱65, store ₱220: where did the gap go?), then the peso, the middle, the ratchet, "Check your food" and the ending. `year_section` and `year_chart` go. Later tickets slot sections 2, 6 and 7 into this order.

Done when:
- [x] `uv run python -m pytest` passes, with `test_the_headlines_tell_the_story_in_order` and the hook tests updated to the March question.
- [x] Review: the first screen of `tmp/local_app.py` asks the onion question with the March numbers.

## Notes
- 2026-11-20: the hook asks March's question. The heroes are "Farmers got, Mar 2023" ₱65 and "Stores charged" ₱220, and the headline asks "Where did the :orange[₱155] go?". The gap is computed from the rounded prices, so it always matches the numbers on screen. The chart is unchanged and still labels January and March.
- Removed `year_section`, `year_chart`, `YEAR_HELP` and `data.farm_fell` with its test. The fixture test still pins tomato's −26%/+13% straight from `price_changes_yearly`.
- The page now has 5 ECharts (hook, peso, dots, middle, ratchet) and 5 so-what lines, and the headline test checks every header, not just the first five. Later tickets update those counts as they add sections.
- Watch the wording: in pesos, the store price fell more than the farm price did (₱468→₱220 against ₱216→₱65), so the line says it "was still ₱220", not that it barely fell.
- Screenshots are in `tmp/shots/` (light and dark, 1440 and 375 px), with no exceptions.
- The owner's page kept opening at "Traders now take…". Each heading's link icon had put `#<heading-id>` in their URL, and the browser scrolls to that id on load. Every title, header and subheader now passes `anchor=False`, held by `test_headings_carry_no_link_so_the_page_always_opens_at_the_top`. Streamlit still gives each heading its id, so an old `#…` URL still jumps; open the bare URL. Restart the dev server after editing `views.py`, since `tmp/local_app.py` keeps the old module.
