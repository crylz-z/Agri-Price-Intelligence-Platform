-- Each food's national farm and store price in the latest month with a farm price,
-- against the same month a year earlier: did the farmer's price and the shopper's
-- move together? The foods with a farmer's share, plus the foods in
-- seeds/change_only_commodities, whose farm price is for another product than the
-- store's (a live hog against a pork cut), so only their percent changes compare.
with share_foods as (
    select month, staple, farmgate_equivalent as farm, retail_price as store,
        cast(null as varchar) as farm_measure
    from {{ ref('int_farmer_share') }}
    where geo_level = 'national'
),

change_only as (
    select month, staple, farm, store, farm_measure
    from {{ ref('int_change_only_prices') }}
),

prices as (
    select * from share_foods
    union all by name
    select * from change_only
),

latest as (select max(month) as month from prices)

select
    now.staple,
    now.month,
    earlier.month as month_year_ago,
    earlier.farm as farm_year_ago,
    now.farm as farm_now,
    earlier.store as store_year_ago,
    now.store as store_now,
    now.farm / earlier.farm - 1 as farm_change,
    now.store / earlier.store - 1 as store_change,
    now.farm_measure
from prices as now
inner join latest on now.month = latest.month
inner join prices as earlier
    on now.staple = earlier.staple
    and earlier.month = now.month - interval 12 month
