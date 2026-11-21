# 03 Context module and section 2, the chain

Status: done
Spec: Context text; Sections (1's vivid line, 2)
Blocked by: 01, 02

`src/dashboard/context.py` holds each hand-written fact with its source, and section 2 shows farmer → trader → wholesaler → store with what each does, what a fair cut pays for and why it matters, from those facts. The hook gets its vivid line if ticket 01 confirmed one.

Done when:
- [x] A test holds that every fact in `context.py` has a source name, URL and date, and `uv run python -m pytest` passes.
- [x] Review: section 2 at 375 px stacks the chain top to bottom with no cut-off text.

## Notes
- 2026-11-20: `src/dashboard/context.py` holds 9 `Fact(text, source, url, date)`. `context.facts()` collects every Fact in the module, so a new fact is checked automatically by `tests/test_context.py`: it needs a source, an https URL and a date in `YYYY[-MM[-DD]]` form, and must open with a capital letter and end with a period. `views.cite(fact)` appends `:gray[([source, year](url))]`.
- Section 2 (`chain_section`) is text only: a header, a line saying "traders" on this page means traders and wholesalers together, four bordered `st.columns` boxes (farmer, trader, wholesaler, store) that stack on a phone, the 3 fair-cut bullets, and a so-what line on poverty. There are no arrows: the columns read left to right, or top to bottom on a phone, and an → would point the wrong way once stacked.
- The hook's chart line now opens with the cited "onions cost more a kilo than chicken or pork" (AFP via Philstar).
- The page now has 6 so-what lines; ECharts are still 5. Ticket 04's receipt joins section 3.
- The poverty fact is cited to "PSA via BusinessWorld", the only reachable copy. Swap in PSA's own page if it ever loads.
- 2026-11-20: Owner reviewed section 2 at phone width and approved it.
