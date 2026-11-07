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
| 1 | Overview | `/` (`?region=…`) | Yearly change of the basket and dish costs, for one region |
| 2 | Compare places | `/places` (`?food=…&level=…`) | One staple's price across provinces or regions |
| 3 | Look up a food | `/lookup` (`?item=…&where=…`) | Any retail price, by commodity and geolocation |

Refer to a page by number and title together, e.g. "page 2 (Compare places)".
_Avoid_: tab, screen, view, story (`views.py` names functions, not pages)
