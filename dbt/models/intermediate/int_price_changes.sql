-- Each food's national farm and store price in the latest month with a farm price,
-- against the same month a year earlier: did the farmer's price and the shopper's
-- move together? Fish is quarterly, so its latest quarter is set against the same
-- quarter a year earlier (months_in_period 3). The foods with a farmer's share, plus the foods in
-- seeds/change_only_commodities, whose farm price is for another product than the
-- store's (a live hog against a pork cut), so only their percent changes compare.
with share_foods as (
    select month, staple, months_in_period,
        farmgate_equivalent as farm, retail_price as store,
        cast(null as varchar) as farm_measure,
        cast(null as varchar) as farm_name,
        cast(null as varchar) as store_name
    from {{ ref('int_farmer_share') }}
    where geo_level = 'national'
),

change_only as (
    select month, staple, 1 as months_in_period, farm, store, farm_measure,
        farm_name, store_name
    from {{ ref('int_change_only_prices') }}
),

prices as (
    select * from share_foods
    union all by name
    select * from change_only
),

latest as (
    select months_in_period, max(month) as month from prices group by months_in_period
)

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
    now.months_in_period,
    now.farm_measure,
    now.farm_name,
    now.store_name
from prices as now
inner join latest
    on now.month = latest.month and now.months_in_period = latest.months_in_period
inner join prices as earlier
    on now.staple = earlier.staple
    and earlier.month = now.month - interval 12 month
