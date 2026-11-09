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
PSA's average price paid to producers at the first point of sale, in pesos per PSA's stated unit (a kilogram for most, a piece for eggs), for one farmgate commodity, geolocation and month.
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
A food's national farm price and store price in the latest month with a farm price, each as a percent change from the same month a year earlier (`price_changes_yearly`). Percent, so a food whose farm price is for another product than its store price (a live hog against pork kasim) still compares.
_Avoid_: year-on-year, YoY, annual change

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
The dashboard's one screen, "Who's eating the farmer's peso?" (`/`, `?food=…` picks the food in section 5).
_Avoid_: tab, view, report

**Section**:
One part of the page, numbered top-down, each a computed headline, one chart (two in section 2) and a so-what line, e.g. "section 2"; each story section opens with one or two big numbers. Read in order, the headlines tell the story: what happened this year, how much reaches the farmer, how prices fall slower than they rise, and whether the gap is growing.

| # | Headline on screen | Plain meaning | Glossary term |
|---|---|---|---|
| 1 | Farmers got X% less for a food this year. You paid Y% more. | The foods whose farm price fell over the past year, beside their store price, biggest split first | Year's change |
| 2 | Farmers get X centavos of your peso | The typical peso split between farmer, traders and stores, then each food's farmer centavos | Typical peso, farmer's share, trader's cut, store's cut |
| 3 | Drop ₱10 at the farm, and you save only ₱X | How far the store price follows the farm price down, against up | Pass-through |
| 4 | The gap grew faster than inflation for N of 18 foods | Foods whose middle's cut grew faster than inflation since 2018, with diesel beside it; whether traders' or stores' centavos of a peso grew more | Middle's cut, verdict, trader's cut, store's cut |
| 5 | Check your food | One food's store price, farm price, traders' and stores' parts, its sections 3 and 4 numbers, and its farmer's share against the typical food's | Farmer's share |

**Typical peso**:
The average farmer's, trader's and store's centavos of a peso over the foods with all three prices (17 of 18; kangkong has no wholesale price), so its parts add up to 100 (`data.typical_peso`). An average, not a median: each part's median need not add up.
_Avoid_: median share, average food

**So-what line**:
The sentence under a section's chart, computed like its headline, that says why the chart matters to a shopper (`views.so_what`), e.g. "So after 3 ups and downs … the store price is ₱6 higher."
_Avoid_: insight, takeaway, conclusion

On screen, a share is in centavos of a peso and a price move in pesos. "Farm price" is the farmgate price, "store price" the retail price, "the gap" the middle's cut, "traders" the trader's cut, "stores" the store's cut, "wholesale" the wholesale price, and "inflation" the CPI's change.
