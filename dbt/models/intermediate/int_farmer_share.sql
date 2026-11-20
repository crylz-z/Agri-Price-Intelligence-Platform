-- How much of a staple's retail price reaches the farmer: the farmgate price, in
-- retail units, over the retail price, same staple, geolocation and month, no lag.
-- Only months with both prices are kept. The wholesale price, when PSA has one,
-- splits the gap into the trader's cut (wholesale - farm) and the store's cut
-- (retail - wholesale). Fish farm prices are quarterly: a fish row is one quarter
-- (month = its first month, months_in_period 3), set against the average retail
-- and wholesale price of its three months, and kept only when all three have one.
with farmgate as (
    select
        prices.month,
        geolocations.geo_code,
        commodities.staple,
        commodities.farmgate_commodity,
        prices.months_in_period,
        prices.price as farmgate_price,
        -- Palay is converted to milled rice: 1 kg of rice takes 1 / 0.63 kg of palay.
        prices.price / commodities.retail_yield as farmgate_equivalent,
        prices.released_at as farmgate_released_at
    from {{ ref('stg_psa__farmgate_prices') }} as prices
    inner join {{ ref('farmgate_commodities') }} as commodities
        on prices.table_id = commodities.table_id
        and prices.commodity = commodities.farmgate_commodity
    inner join {{ ref('farmgate_geolocations') }} as geolocations
        on prices.geo_label = geolocations.label
    where prices.snapshot_rank = 1
        -- PSA fills farmgate cells with no sales with 0.00, not "..".
        and prices.price > 0
        and not exists (
            select 1 from {{ ref('farmer_share_exclusions') }} as exclusions
            where exclusions.geo_code = geolocations.geo_code
                and exclusions.staple = commodities.staple
        )
),

wholesale as (
    select
        prices.month,
        geolocations.geo_code,
        commodities.staple,
        prices.price as wholesale_price,
        prices.released_at as wholesale_released_at
    from {{ ref('stg_psa__wholesale_prices') }} as prices
    inner join {{ ref('wholesale_commodities') }} as commodities
        on prices.table_id = commodities.table_id
        and prices.commodity = commodities.wholesale_commodity
    inner join {{ ref('farmgate_geolocations') }} as geolocations
        on prices.geo_label = geolocations.label
    where prices.snapshot_rank = 1 and prices.price > 0
),

-- The retail and wholesale price over each farm price's period: the month itself,
-- or a fish quarter's three months, averaged.
retail as (
    select
        farmgate.month,
        farmgate.geo_code,
        farmgate.staple,
        any_value(prices.geolocation) as geolocation,
        any_value(prices.geo_level) as geo_level,
        any_value(prices.category) as category,
        any_value(prices.unit) as unit,
        avg(prices.price) as retail_price,
        max(prices.released_at) as retail_released_at
    from farmgate
    inner join {{ ref('int_staple_prices') }} as prices
        on farmgate.geo_code = prices.geo_code
        and farmgate.staple = prices.staple
        and prices.month >= farmgate.month
        and prices.month < farmgate.month + to_months(farmgate.months_in_period)
    group by farmgate.month, farmgate.geo_code, farmgate.staple
    having count(*) = any_value(farmgate.months_in_period)
),

wholesale_period as (
    select
        farmgate.month,
        farmgate.geo_code,
        farmgate.staple,
        avg(wholesale.wholesale_price) as wholesale_price,
        max(wholesale.wholesale_released_at) as wholesale_released_at
    from farmgate
    inner join wholesale
        on farmgate.geo_code = wholesale.geo_code
        and farmgate.staple = wholesale.staple
        and wholesale.month >= farmgate.month
        and wholesale.month < farmgate.month + to_months(farmgate.months_in_period)
    group by farmgate.month, farmgate.geo_code, farmgate.staple
    having count(*) = any_value(farmgate.months_in_period)
),

shares as (
    select
        farmgate.month,
        farmgate.geo_code,
        retail.geolocation,
        retail.geo_level,
        farmgate.staple,
        retail.category,
        retail.unit,
        farmgate.months_in_period,
        farmgate.farmgate_commodity,
        farmgate.farmgate_price,
        farmgate.farmgate_equivalent,
        retail.retail_price,
        farmgate.farmgate_equivalent / retail.retail_price as farmer_share,
        retail.retail_price - farmgate.farmgate_equivalent as peso_gap,
        wholesale.wholesale_price,
        wholesale.wholesale_price - farmgate.farmgate_equivalent as trader_cut,
        retail.retail_price - wholesale.wholesale_price as store_cut,
        farmgate.farmgate_released_at,
        retail.retail_released_at,
        wholesale.wholesale_released_at
    from farmgate
    inner join retail
        on farmgate.month = retail.month
        and farmgate.geo_code = retail.geo_code
        and farmgate.staple = retail.staple
    left join wholesale_period as wholesale
        on farmgate.month = wholesale.month
        and farmgate.geo_code = wholesale.geo_code
        and farmgate.staple = wholesale.staple
)

select
    *,
    -- Each staple's own latest month with both prices, per geolocation.
    month = max(month) over (partition by geo_code, staple) as is_latest
from shares
