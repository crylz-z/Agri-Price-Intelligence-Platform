# APIP

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
