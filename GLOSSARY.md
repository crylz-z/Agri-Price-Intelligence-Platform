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
An everyday food under its plain name, mapped to exactly one commodity: "Pechay" is PSA's `PECHAY, NATIVE, 1 KG`. The farmer's share and dish costs are counted per staple.
_Avoid_: item, product, good

**Basket**:
The fixed set of staples the stories track (`dbt/seeds/staples.csv`).
_Avoid_: shopping list, CPI basket

**Recipe**:
The fixed quantities of staples for one dish, for one meal for a family of 5, rice included, scaled from a published recipe where one was found.
_Avoid_: menu, meal plan

**Dish cost**:
The sum of retail price × quantity over a recipe's staples for one geolocation and month; blank when any staple has no price there.
_Avoid_: meal price, ulam price

**Seasonal index**:
How far a staple's national price usually sits above or below its centred 13-month average in a calendar month.
_Avoid_: seasonality factor, best month

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

**Suspect**:
A party the public record accuses of taking part of the middle's cut for a staple, cited from a House finding, a PCC charge or published research.
_Avoid_: villain, culprit, cartel (on screen, unless a finding uses the word)

**Verdict**:
A staple's computed label each release: suspicious when its middle's cut grew faster than inflation since 2018, cleared otherwise.
_Avoid_: rating, score, grade

**Dish wage share**:
A dish cost as a share of the region's daily non-agriculture minimum wage in force that month.
_Avoid_: affordability index, wage-hours

**Wage order**:
One regional wage board order that sets a region's daily minimum wage from an effective date.
_Avoid_: wage hike, wage rate

**Policy event**:
A dated government action on a staple's supply or price, such as an import suspension, a tariff change or a palay floor price.
_Avoid_: intervention, news, announcement

## Checks

**Spot check**:
A price looked up from PSA by hand, outside the pipeline, and stored with its table, geolocation and month (`psa_spot_checks.csv`, `psa_farmgate_spot_checks.csv`); a test fails when the pipeline's price differs. For a seed typed in from a source, such as `wage_orders.csv`, a spot check is a person comparing a few rows against that source.
_Avoid_: sample test, sanity check

## Dashboard

**Caveat**:
A short note beside a chart or number that names a known limit of the data behind it, such as a region with no wage order or a price whose unit is in doubt.
_Avoid_: disclaimer, warning, footnote

**Page**:
One screen of the dashboard, named by its sidebar title. Numbered in sidebar order:

| # | Title | URL | Shows |
|---|---|---|---|
| 1 | Farm to plate | `/` (`?region=…&staple=…`) | Farmer's share per staple, one staple's farmgate and retail prices with policy events, and dish wage share for one region |
| 2 | Overview | `/overview` (`?region=…`) | Yearly change of the basket, for one region |
| 3 | Compare places | `/places` (`?food=…&level=…`) | One staple's price across provinces or regions |
| 4 | Look up a food | `/lookup` (`?item=…&where=…`) | Any retail price, by commodity and geolocation |

Refer to a page by number and title together, e.g. "page 3 (Compare places)".

**Card**:
One bordered box on a page, numbered in reading order, e.g. "page 1 card 2". KPI tiles are not cards. Page 1 (Farm to plate) reads: 3 KPI tiles → card 1 (left) beside card 2 (right) → card 3. On a phone the cards stack 1, 2, 3.

| Card | Title on screen | Plain meaning | Glossary term |
|---|---|---|---|
| 1 | Farmer's cut of every ₱100 | Pesos the farmer gets when a shopper spends ₱100 on that food; clicking a bar picks that food in card 2 | Farmer's share |
| 2 | Farm and store price, per kg | One food (picked in its selectbox or by a card 1 click) priced at the farm and at the store over the years; dashed lines mark government policies | Farmgate price, retail price, policy event |
| 3 | Dinner for 5, as a share of a day's minimum wage | How much of one day's minimum pay a family dinner costs; over 100% means more than a day's pay | Dish wage share |

On screen, "farm price" is the farmgate price, "store price" the retail price, and "policy" a policy event.
_Avoid_: box, section, panel, widget
_Avoid_: tab, screen, view, story (`views.py` names functions, not pages)
