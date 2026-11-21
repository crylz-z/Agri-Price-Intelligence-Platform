# 06 Section 7, what can be done

Status: done
Spec: Sections (7); Context text
Blocked by: 01, 05

Section 7 says what is being done (PCC enforcement, Kadiwa stores) and where to report overpricing, from cited facts in `context.py`, with no policy positions.

Done when:
- [x] `uv run python -m pytest` passes, and the headline order test includes section 7.
- [x] Review: every claim in section 7 links to its source.

## Notes
- 2026-11-21: `views.remedy_section` is section 7, after "Who got caught": header "What can be done", then "Being done" (`context.BEING_DONE`: PCC powers under RA 10667, the tripled fine for staples, RA 12022's economic sabotage, KADIWA ng Pangulo) and "Where to report" (`context.REPORT`: the PCC portal and email, a DOJ complaint under RA 12022). Each fact is cited, so the chain test's every-fact check covers them; `test_context.py` adds a no-"should/must" check.
- Not as specced: no DTI or DA hotline. `sources.md` found no DA price-complaint hotline, and DTI's 1-384 rests on a search summary (dti.gov.ph returned 404), so neither has a source to cite. The owner left both out and passed the review (2026-11-21).
- Owner asked mid-ticket for arrows between the chain's boxes: narrow columns holding `views.CHAIN_ARROW`, keyed `chain_arrow_<i>`; app.py's CSS centres them and turns the icon down below 640 px. Rotate the icon (`[role="img"]`), never the full-width Markdown container, which swings across the boxes.
- Ticket 08 (motion) should check the arrows in mid-scroll frames too.
