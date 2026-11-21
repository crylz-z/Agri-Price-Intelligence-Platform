# Story v5: the short version, a clearer hook, chapters and the dumbbell

## Why
A reader short on time, or with ADHD, can't get the finding today without reading every chart over four pages. Page 1 also opens confusingly: ₱65 shows three times before the guess, and a line about October 2026 rice sits above a question about March 2023 onions. Big blank gaps between sections read as missing content, and page 2's "+67 pts" bars ask the reader to subtract two percentages in their head. The reader should get the point, and why it matters, with no charts.

## Outcome
Five pages: story → who got caught → check your food → **the short version** → how it's built. The short version says the whole finding in plain bullets, each the answer to a professor's "so what?". Page 1 opens straight on the onion question.

## Decisions
- **Newest-month line:** it leaves the top of page 1. Its news becomes a bullet in the short version, plus a short grey caption in the masthead row ("Updated with PSA's October 2026 release").
- **Hook before the guess:** no big number. ₱65 appears only in the headline. The slider's label reads "Drag to guess" and the slider doesn't start out showing ₱65. After "Show me", the screen is unchanged.
- **Chapter labels:** a small grey label above each section on pages 1 and 2 fills the gaps, with each page counting its own sections ("2 of 5 · Where your peso goes").
- **Page 2's growth chart becomes a dumbbell:** per food, a blue farm-growth dot and an ink store-growth dot since 2018, joined by an amber line where the store outran the farm and a grey line where the farm kept up. Labels show both percents ("farm +40%, store +107%"). It uses the same data: `farm_change` and `store_change` in `growth_since_2018`.
- **Short version, place:** a new page between "Check your food" and "How it's built" (`nav.PAGES`). Page 1 gets one line near the top: "Short on time? Read the short version →".
- **Short version, name:** the tab reads "The short version". A small grey "TL;DR" label sits above the title.
- **Short version, each bullet:** a bold direct finding, then the plain "so what": what it means for the reader or the farmer, said straight, as an answer to a professor. At most one number, rounded and in pesos per ₱100 where it's a share. Every number is computed live, like the headlines. For example: "**Farmers get less than half of what you pay.** So most of your money feeds the traders and stores between the farm and you, not the person who grew it."
- **Short version, bullets in order:** the onion gap; who's in the chain; the farmer's part; traders' part rising since 2018; a ₱10 farm drop saving you only ₱8; it's every food; it's not new; who got caught; the newest month's news; one bullet on the fix on the record, worded as its source words it.
- **Short version, no charts and no per-bullet links.** It closes on two links: "Want the proof? Read the full story →" and "Check your own food →".
- **No new ADR.** The owner asked for none.

## Free calls
Slider mechanics, the chapter names, the dumbbell's sort order and phone density, the exact bullet wording within the rules above, the page file layout.

## Checklist
- [ ] Short version page, end to end: a new page in `nav.PAGES` and `app_pages/`, the bullets computed in `data.py` with tests, and a page test that renders it offline — done when `pytest` passes, the new page renders in `test_pages.py` with every bullet present, and every sentence opens with a word.
- [ ] Page 1 link to the short version, and the newest-month line moved to the masthead caption and the short version — done when the page test finds the link and no "New for" line under the title.
- [ ] Hook before the guess: no hero, ₱65 once, "Drag to guess" — done when a page test before the click counts one "₱65" on screen.
- [ ] Chapter labels on pages 1 and 2 — done when the page tests find "N of M" labels in order on both pages.
- [ ] Dumbbell on page 2, replacing `middle_chart` — done when its test checks both percents in the labels, and screenshots at 375 and 1440 px, light and dark, pass the `screenshot-checker`.
- [ ] Prune `.claude/rules/dashboard.md`: update what this change makes stale ("four pages", the newest-month line, the hook, the "+pts" chart), add the short version's bullet rule in one line, and cut any line in the touched sections that repeats code or another rule — done when a grep for "four pages", "newest_line" and "pts" there returns only live facts, and the file is no longer than now (47 lines).
- [ ] Full check: `pytest`, `pre_commit run --all-files`, and screenshots of all five pages at 375 and 1440 px, light and dark — done when all pass.

## Review
- Does the short version, read alone, tell you the finding and why it matters?
- The page 1 opening before the guess.
- Whether the chapter labels make the gaps feel intentional.
- Whether the dumbbell reads at a glance on a phone.

## Log
