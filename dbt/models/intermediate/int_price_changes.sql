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
    select farm.month, seeds.staple, farm.price as farm, store.price as store,
        seeds.farm_measure
    from {{ ref('stg_psa__farmgate_prices') }} as farm
    inner join {{ ref('change_only_commodities') }} as seeds
        on farm.table_id = seeds.table_id
        and farm.commodity = seeds.farmgate_commodity
    inner join {{ ref('int_staple_prices') }} as store
        on store.staple = seeds.staple
        and store.month = farm.month
        and store.geo_level = 'national'
    where farm.snapshot_rank = 1
        and farm.geo_level = 'national'
        -- PSA fills farmgate cells with no sales with 0.00, not "..".
        and farm.price > 0
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
