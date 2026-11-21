# PH Food Prices

Monthly retail food prices across the Philippines, as published by the Philippine Statistics Authority (PSA).

## Publication

**Table**:
PSA's unit of publication: all retail prices for one commodity group, across every geolocation and month.
_Avoid_: dataset, endpoint, file

**Release**:
One publication of a table by PSA, identified by the table's `updated` timestamp.
_Avoid_: update, version, refresh

**Snapshot**:
The unchanged copy of one table as of one release.
_Avoid_: dump, export, backup

**Revision**:
A change to an already-published month's price that appears in a later release.
_Avoid_: correction, restatement

## Prices

**Retail price**:
PSA's reported average consumer price, in pesos per the commodity's stated unit, for one commodity, geolocation and month.
_Avoid_: cost, value, rate

**Commodity**:
One specific item with its unit, named as PSA names it, e.g. `RICE, WELL-MILLED, 1 KG`.
_Avoid_: product, item, SKU

**Commodity group**:
PSA's category of commodities, such as Cereals or Fish. Each group is published as one table.
_Avoid_: category, sector

**Month**:
The calendar month a retail price describes, not the date it was published.
_Avoid_: period, date, posting date

## Geography

**Geolocation**:
The area a retail price applies to: the Philippines as a whole, a region, or a province or city.
_Avoid_: location, area, place

**Geo level**:
Which tier a geolocation sits on: national, region or province.
_Avoid_: granularity, scope

## Basket

**Staple**:
An everyday food under its plain name, mapped to exactly one commodity: "Pechay" is PSA's `PECHAY, NATIVE, 1 KG`. The farmer's share and the verdict are counted per staple.
_Avoid_: item, product, good

**Basket**:
The fixed set of staples the stories track (`dbt/seeds/staples.csv`).
_Avoid_: shopping list, CPI basket

## Farm to retail

**Farmgate price**:
PSA's average price paid to producers at the first point of sale, in pesos per PSA's stated unit (a kilogram for most, a piece for eggs), for one farmgate commodity, geolocation and month (a quarter for fish, whose row is set against the quarter's average retail and wholesale price).
_Avoid_: producer price, farm price, buying price

**Farmer's share**:
A staple's farmgate price as a share of its retail price, for the same geolocation and month; palay is first converted to milled rice.
_Avoid_: markup, margin, spread

**Middle's cut**:
A staple's retail price minus its farmgate price (palay as milled rice), in pesos per unit: what traders, transport, storage and stores together take (`peso_gap` in the marts).
_Avoid_: markup, margin, spread, peso gap

**Wholesale price**:
PSA's average wholesale selling price, what traders sell to stores for, in the retail unit, for one wholesale commodity, geolocation and month.
_Avoid_: trader price, bulk price

**Trader's cut**:
The part of the middle's cut between farm and wholesale: wholesale price minus farmgate price (`trader_cut`).
_Avoid_: middleman's margin, trader markup

**Store's cut**:
The part of the middle's cut between wholesale and shelf: retail price minus wholesale price (`store_cut`).
_Avoid_: retail margin, retailer markup

**Suspect**:
A party the public record accuses of taking part of the middle's cut for a staple, cited from a House finding, a PCC charge or published research.
_Avoid_: villain, culprit, cartel (on screen, unless a finding uses the word)

**Verdict**:
A staple's computed label each release: suspicious when its middle's cut grew faster than inflation since 2018, cleared otherwise.
_Avoid_: rating, score, grade

**Year's change**:
A food's national farm price and store price in the latest month with a farm price (fish: the latest quarter), each as a percent change from a year earlier (`price_changes_yearly`). Percent, so a food whose farm price is for another product than its store price (a live hog against pork kasim) still compares.
_Avoid_: year-on-year, YoY, annual change

**Growth since 2018**:
A food's national farm price and store price averaged over the last 12 months, each as a percent change from its 2018 average (`growth_since_2018`), meat included. A store price that grew faster than the farm price means the middle grew.
_Avoid_: long-run change, trend

**Pass-through**:
How many pesos a staple's retail price moves per peso its farmgate price moves, in 2018 pesos (deflated by CPI), counted separately over months when the farmgate price rose (up) or fell (down) more than 15% from a year earlier. Below 1 on the way down means shoppers never saw part of the fall.
_Avoid_: asymmetry, stickiness, rockets and feathers

## Checks

**Spot check**:
A price looked up from PSA by hand, outside the pipeline, and stored with its table, geolocation and month (`psa_spot_checks.csv`, `psa_farmgate_spot_checks.csv`); a test fails when the pipeline's price differs.
_Avoid_: sample test, sanity check

## Dashboard

**Caveat**:
A short note beside a chart or number that names a known limit of the data behind it, such as rice's converted farmgate price or a month when the farmer's share tops 100%.
_Avoid_: disclaimer, warning, footnote

**Page**:
The dashboard's one screen, "Who's eating the farmer's peso?" (`/`, `?food=…` picks the food in section 8).
_Avoid_: tab, view, report

**Section**:
One part of the page, numbered top-down, e.g. "section 3". Read in order, the sections solve a mystery (ADR 24): a question the reader feels, who stands between farm and store, whether the gap is everywhere, growing and sticky, who was caught, what can be done, then one food of the reader's choosing and a one-line ending. A data section carries a computed headline, a chart and a so-what line; a context section may be text only, each fact with a cited source.

| # | Section | Plain meaning | Glossary term |
|---|---|---|---|
| 1 | The hook | March 2023: farmers sold onions for ₱65 a kilo, stores still charged ₱220. Where did the gap go? | Farmer's share, middle's cut |
| 2 | The chain | Who stands between farm and store, and what a fair cut pays for (trucking, storage, spoilage) | Middle's cut |
| 3 | Is it only onions? | The typical peso split between farmer, traders and stores, shown as a receipt, then each food's farmer centavos | Typical peso, receipt |
| 4 | It's growing | Traders' centavos of a peso in 2018 and now, then each food's farm and store growth since 2018 against inflation | Trader's cut, growth since 2018 |
| 5 | It sticks | How far the store price follows the farm price down, against up, drawn as an example | Pass-through |
| 6 | Who got caught | The public record, rulings first | Public record, suspect |
| 7 | What can be done | What is being done, and what the reader can do | |
| 8 | Check your food | One food's store price, farm price, traders' and stores' parts, its gap's growth and moves, and its farmer's share against the typical food's. Meat: its two prices, then each one's change over the year and since 2018 | Farmer's share, year's change |
| 9 | The ending | One computed line | Typical peso |

**Receipt**:
An example shopping basket drawn as a receipt, each line's price split into the farmer's, traders' and stores' pesos. The basket is our pick and is labelled an example on screen.
_Avoid_: basket chart, cart

**Public record**:
The cited claims about who takes part of the middle's cut (`dbt/seeds/suspects.csv`): rulings, findings and charges, plus allegations labelled "alleged". Opinions stay out.
_Avoid_: evidence, proof, receipts

**Typical peso**:
The average farmer's, trader's and store's centavos of a peso over the foods with all three prices (20 of 21; kangkong has no wholesale price, and meat has no farmer's share), so its parts add up to 100 (`data.typical_peso`). An average, not a median: each part's median need not add up.
_Avoid_: median share, average food

**So-what line**:
The sentence under a section's chart, computed like its headline, that says why the chart matters to a shopper (`views.so_what`), e.g. "So the farm price is back where it started, but the store price is ₱2 higher."
_Avoid_: insight, takeaway, conclusion

On screen, a share is in centavos of a peso and a price move in pesos. "Farm price" is the farmgate price, "store price" the retail price, "the gap" the middle's cut, "the middle" the traders and stores who take it, "traders" the trader's cut, "stores" the store's cut, "wholesale" the wholesale price, and "inflation" the CPI's change.
