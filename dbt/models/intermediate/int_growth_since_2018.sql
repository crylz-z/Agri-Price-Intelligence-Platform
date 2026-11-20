-- Each food's national farm and store price, averaged over 2018 ("then") and
-- over the 12 months to the latest month in int_farmer_share ("now"), the same
-- windows as int_food_verdicts: how much did each grow? Foods with a farmer's
-- share (fish averages its quarters), plus the change-only foods (meat), whose
-- farm price is for another product (a live hog), so only the growth compares,
-- never the pesos. inflation is the all-items CPI over the same months.
with share_foods as (
    select month, staple, farmgate_equivalent as farm, retail_price as store,
        false as change_only
    from {{ ref('int_farmer_share') }}
    where geo_level = 'national'
),

change_only as (
    select month, staple, farm, store, true as change_only
    from {{ ref('int_change_only_prices') }}
),

prices as (
    select * from share_foods
    union all by name
    select * from change_only
),

windows as (
    select
        date '2018-01-01' as then_start,
        date '2018-12-01' as then_end,
        max(month) - interval 11 month as now_start,
        max(month) as now_end
    from share_foods
),

averages as (
    select
        prices.staple,
        any_value(prices.change_only) as change_only,
        avg(prices.farm) filter (where prices.month <= windows.then_end
            and prices.month >= windows.then_start) as farm_then,
        avg(prices.farm) filter (where prices.month >= windows.now_start
            and prices.month <= windows.now_end) as farm_now,
        avg(prices.store) filter (where prices.month <= windows.then_end
            and prices.month >= windows.then_start) as store_then,
        avg(prices.store) filter (where prices.month >= windows.now_start
            and prices.month <= windows.now_end) as store_now
    from prices cross join windows
    group by prices.staple
),

cpi as (
    select
        avg(cpi.cpi) filter (where cpi.month between windows.now_start and windows.now_end)
            / avg(cpi.cpi) filter (where cpi.month between windows.then_start and windows.then_end)
            - 1 as cpi_change
    from {{ ref('stg_psa__cpi') }} as cpi cross join windows
    where cpi.commodity = '0 - ALL ITEMS'
)

select
    averages.staple,
    averages.change_only,
    windows.now_start,
    windows.now_end,
    averages.farm_then,
    averages.farm_now,
    averages.store_then,
    averages.store_now,
    averages.farm_now / averages.farm_then - 1 as farm_change,
    averages.store_now / averages.store_then - 1 as store_change,
    cpi.cpi_change
from averages
cross join windows
cross join cpi
where averages.farm_then is not null and averages.farm_now is not null
    and averages.store_then is not null and averages.store_now is not null
