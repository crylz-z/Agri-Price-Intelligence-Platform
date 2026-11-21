# 04 The receipt in section 3

Status: done
Spec: The receipt; Sections (3)
Blocked by: 03

`data.receipt` splits the spec's example basket into you pay, farmer, traders and stores, in pesos, from the latest national month, and section 3 shows it as a receipt with a total row, labelled an example, above each food's farmer centavos.

Done when:
- [x] `tests/test_dashboard_data.py` checks `data.receipt` against hand-worked numbers, including galunggong's quarter, and `uv run python -m pytest` passes.
- [x] Review: each receipt row's farmer, traders and stores add up to its "you pay", and the total row adds up its columns.

## Notes
- 2026-11-20: `data.BASKET` and `data.receipt(shares)` give one row per food (`item`, `month`, `months`, `pay`, `farmer`, `traders`, `stores`) plus a `Total` row. Each line is whole pesos split by largest remainder (`whole_centavos`), so a line always adds up and the total row is the column sums. A food without a wholesale price that month drops out.
- `views.receipt_table` draws it with `st.table(border="horizontal")`: Markdown cells give the Farmer and Traders headers their role colours and bold the total. Its caption names the most common month and lists the others, e.g. "(rice October 2026; galunggong July–September 2026)" on the live lake.
- The receipt replaces v2's typical-peso bar (owner's choice, recorded in the spec): `peso_chart` and `STORE_GREY` are gone, section 3's big numbers are farmer 46¢ and traders 21¢, and the page now has 4 ECharts (hook, dots, middle, ratchet), so the `echarts()` indexes in `test_pages.py` shifted.
- Section 3's traders 21¢ (an average) and section 4's "Now 21¢" (a median) coincide on today's data. The owner's read-through (ticket 09) may want to tell them apart.
