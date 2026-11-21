# 05 Section 6, who got caught

Status: done
Spec: The public record; Sections (6)
Blocked by: 01, 04

Section 6 shows the public record, rulings first, always on: `views.SHOW_RECORD` and its tests go, and the opinion row leaves `dbt/seeds/suspects.csv`.

Done when:
- [x] `uv run python -m pytest` passes, with a test that every record row on the page has a source URL and date, and none is an opinion.
- [x] Review: the owner has checked each record source by hand (ticket 01's notes) before this ships.

## Notes
- 2026-11-21: `views.record_section` is section 6, between the ratchet and "Check your food": header "Who got caught", one line saying our prices can't name anyone, then each `suspect` row as claim, grey status and linked source with its date. `SHOW_RECORD`, `record` and the "On the record" subheader are gone.
- `suspects.csv` is reworded from `sources.md`: the PCC row cites the PCC's own release (announced 15 Oct 2026, fines not final), a new NBI complaint row (Philstar 2023-09-20), the House row without the cold-storage claim, rice as one lawmaker's ₱13 billion, Benguet's 42% as a national figure, and the DZRH opinion row is dropped. Rows sit rulings, charges, findings, allegations; the page keeps that order, and the spec now says so.
- `test_the_public_record_is_on_the_page_rulings_first_each_sourced` (pages) and `test_suspects_seed_has_a_dated_source_for_every_claim_and_no_opinion` (data) hold the gate. `data.claims_for` is now read only by its test; a later cleanup may drop it.
- Ticket 06 goes between `record_section()` and "Check your food" in `case_page`; "Check your food" is already commented 8, leaving 7 for it.
- For the owner's hand-check: the NBI and House rows rest on Philstar and BusinessMirror (secondary), and the PCC row on the PCC's primary release. The owner passed all of them (2026-11-21).
