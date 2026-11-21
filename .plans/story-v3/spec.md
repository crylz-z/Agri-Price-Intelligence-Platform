# Story v3: the farmer's peso as a mystery

Rewrites the one page, "Who's eating the farmer's peso?" (`src/dashboard/`), for a reader who knows nothing about farm prices and doesn't follow the news. It opens on a question they feel, explains who stands between farm and store, shows the gap is everywhere, growing and sticky, names who was caught, and ends on what can be done. Decided 2026-11-20 (ADR 24).

## Problem
The owner, viewing story v2: "There's no one to blame. Why is this happening? How would this affect me? Why should I care as a reader?" The page shows a pattern with no actor (the public record is hidden behind `views.SHOW_RECORD`), no cause (causes sit in tooltips a newcomer never opens), no stake in the reader's own money (centavos per kilo), and no problem it sets out to solve.

## Solution
A page that reads as a mystery with an answer and a way out:
- A reader can feel the problem in the first screen: farmers sold onions for ₱65 a kilo while stores charged ₱220, so where did the ₱155 go?
- A reader can learn who traders, wholesalers and stores are, and what a fair cut pays for, so a later finding reads as wrongdoing rather than as all margins being theft.
- A reader can see their own shopping split on a receipt, so the gap is in pesos they recognise.
- A reader can see the gap is in most foods, growing since 2018, and slower to fall than to rise.
- A reader can see who regulators caught, each claim cited and worded as its source words it.
- A reader can learn what is being done and what they can do, each fact cited.
- A reader can still check one food of their choosing.

## Decisions
### Reader and voice
- The reader knows nothing of farm prices and doesn't watch the news; they arrive from a shared post, on a phone.
- They leave with a target backed by numbers: who regulators caught, and proof the gap is not a one-off.
- Plain English. A Filipino version is later work.
- The title stays "Who's eating the farmer's peso?": section 6 answers it.

### Sections (`GLOSSARY.md` → Section holds the table)
1. **The hook.** The onion crash in March 2023: farm ₱65, store ₱220 a kilo (national, `farmer_share_monthly`), asked as a question. It uses the farm price's lowest month (`data.hook`'s low), replacing story v2's January peak (₱468 against ₱216), because 30 centavos is a sharper contrast than 46. One cited line makes the crisis vivid to a reader who missed it ("onions cost more than meat"), if research confirms it.
2. **The chain.** Mostly text and a simple picture of farmer → trader → wholesaler → store, saying who each is, plus what a fair cut pays for (trucking, storage, spoilage) and why it matters (farmers among the poorest workers). Each fact cited. The picture uses stock Streamlit (columns with icons and arrows, stacking on a phone), since ECharts adds nothing to four boxes.
3. **Is it only onions?** The receipt, then each food's farmer centavos (`farmer_dots`, kept). The receipt replaces v2's typical-peso bar (owner, 2026-11-20); the typical peso's farmer and traders centavos (46¢ and 21¢ in v2) become the two big numbers, and stores' part stays in the so-what line.
4. **It's growing.** Story v2's middle section, kept: traders' centavos in 2018 and now, then each food's farm and store growth since 2018 against inflation.
5. **It sticks.** Story v2's ratchet, kept.
6. **Who got caught.** The public record, rulings first. Always on the page: `views.SHOW_RECORD` goes.
7. **What can be done.** What is being done (the PCC fining cartels, DA's Kadiwa stores selling straight from farmers) and where to report overpricing (the PCC; a DOJ complaint). No DTI or DA hotline has a citable source, so the owner left them out (2026-11-21). Facts only, no policy positions, each cited.
8. **Check your food.** Kept as is.
9. **The ending.** Kept: one computed line.
- Story v2's section 2 ("Farmers got X% less for a food this year", `year_section`, `year_chart`) is cut: with November 2026 data it rests on 1 food of 1. `price_changes_yearly` stays, since "Check your food" reads it.

### The receipt
- An example basket, labelled an example on screen: 1 kg regular rice, 1 kg galunggong, 1 kg tomato, ½ kg red onion, 12 eggs. Each has a farm, wholesale and store price; meat is left out because it can't be split in pesos.
- Each line: item and quantity, you pay, farmer, traders, stores, in pesos from the latest national month (galunggong: its latest quarter, named with `views.when`). A total row sums each column.
- A new `data.receipt` helper computes it from `farmer_share_monthly`, with a hand-worked test in `tests/test_dashboard_data.py`. The basket and quantities live in `data.py` as a constant.

### The public record
- Shows rulings, findings and charges, plus allegations labelled "alleged". Opinions stay out: drop the DZRH row (a former DA secretary's opinion) from `dbt/seeds/suspects.csv`.
- Rulings first: the PCC onion cartel fine (announced 15 Oct 2026, per the PCC; corrected from "decided 1 Oct" by `sources.md`) leads. The seed keeps rulings, charges, findings, then allegations, and the page keeps the seed's order.
- Wording stays "found", "charged" or "alleged"; no private person is named; blame never comes from our prices alone (ADR 14).

### Context text
- Data numbers stay computed from the marts. Context text (sections 2 and 7, the hook's vivid line, causes named in the main text) is written by hand, each fact with a cited source.
- Context facts live in one module, `src/dashboard/context.py`, each with its text, source name, URL and date, so a test can hold that every fact carries a source. Its facts come from the research in ticket 01.
- Causes may be named in the main text, fair (costs) and unfair (cartels, hoarding), each cited, never inferred from our prices.

### Rules that change
- `.claude/rules/dashboard.md` follows ADR 24: a context section may be text only; hand-written context with a cited source is allowed beside computed headlines; causes may sit in the main text; the record is on the page.
- Kept: national data only, numbers from tested marts, plain words on screen, one palette, no private individuals.

### Engagement (owner, 2026-11-21)
The owner found sections 6 and 7 read like an article. The reader should act, not only scroll. Ideas taken from the `diagram-design` skill (timeline, steps), built in stock Streamlit; the skill itself is not adopted.
- **The hook asks for a guess first.** Before the store price shows, the headline asks "In March 2023, farmers got ₱65 for a kilo of onions. What do you think stores charged?" with a slider ("Your guess", ₱5 steps, from the farm price to twice the store price rounded up to ₱50) and a "Show me" button. Only the farm big number shows until then. After it: the hook as before, plus one line saying how far the guess was from the store price. The guess lives in `st.session_state["hook_guess"]`, so a rerun keeps it.
- **Who got caught is case cards.** A big number leads: fined so far (amber, the sum of the seed's `fine_php`, labelled with the ruling's month). Then each suspect row is a bordered card: a grey badge for its stage (Ruling, Charged, Finding, Alleged; the seed's new `stage` column: ruling, charge, finding, allegation, and research for alibi rows), the claim, then the grey status and linked source. Rulings first, as before.
- **What can be done is cards and a button.** "Being done" is a grid of bordered cards, two across on a wide screen, one on a phone, each with an icon, a short title and its cited fact (`context.BEING_DONE` holds title, icon and fact, like `CHAIN`). "Where to report" opens with a primary button, "Report a cartel to the PCC", linking to the PCC's portal, then the cited facts.
- Badges and cards stay grey or plain: colour keeps its roles (blue farmer, amber the middle).

- **The ratchet is a toy (owner, 2026-11-21).** Past the hook the page read like an article, so the reader should play, not read. Of the ideas offered (a guess before every reveal, the ratchet toy, your own receipt, a scorecard), the owner took only the toy. Section 5's 3-swing animation became "Farm price +₱10", "Farm price −₱10" and "Start over" buttons; the chart draws the reader's presses (up to 8, the farm at most ₱30 below its start). The amber bracket marks how far the store ended above a peso-for-peso store. The so-what is computed from the presses and shows after the first one. The 3-swing prose left with the animation, because the toy shows it.
- **Lighter reading (owner, 2026-11-21).** Each headline tooltip is one line plus at most three short bullets. Traders' part shows only in section 4: section 3's big number (latest month, mean) disagreed with section 4's (last 12 months, median) by a centavo.

### Motion
- The hook chart jerks at the end of its entry animation (owner, 2026-11-20). Find the cause with Playwright frames and fix it; then rerun the scroll-motion check skipped after v2's redesign.

## Verification
- Seam: `tests/test_pages.py`, which renders the whole page offline from `tests/fixtures/marts/`; data helpers in `tests/test_dashboard_data.py`.
- `uv run python -m pytest` and `uv run python -m pre_commit run --all-files` pass.
- The headlines, read in order, follow the 9 sections above (`test_the_headlines_tell_the_story_in_order`).
- Every fact in `context.py` and every record row has a source URL and date (a test).
- Screenshots from `scripts/screenshot.py` at 1440 and 375 px, light and dark, from `tmp/local_app.py`: no cut-off text, no horizontal scroll, no exceptions.
- The owner reads the page top to bottom and can answer: who is to blame, why it happens, how it affects them, what they can do.

## Out of scope
- A Filipino or Taglish version: a separate translation job.
- A household's monthly cost to the middle: needs PSA family spending data (FIES), a new source.
- Policy positions: facts only, so critics can't dismiss the data with the opinion.
- The video, push and PR: after the owner asks.
- Deleting the old R2 marts and pechay's 2026 dip: on the backlog.
