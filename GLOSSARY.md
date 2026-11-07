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
An everyday food under its plain name, such as "Galunggong", mapped to exactly one commodity.
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

## Dashboard

**Page**:
One screen of the dashboard, named by its sidebar title. Numbered in sidebar order:

| # | Title | URL | Shows |
|---|---|---|---|
| 1 | This month | `/` (`?region=…`) | Change over time for one region |
| 2 | Where you live | `/places` (`?place=…`) | One month compared across places |
| 3 | Ulam cost | `/ulam` | Dish costs |
| 4 | When to buy | `/seasons` | Seasonal index per staple |
| 5 | Look up a price | `/lookup` | Any retail price, by commodity and geolocation |

Pages 1–4 sit under "Stories" in the sidebar, page 5 under "Explore". Refer to a page by number and title together, e.g. "page 2 (Where you live)".
_Avoid_: tab, screen, view, story (`views.py` names functions, not pages)
