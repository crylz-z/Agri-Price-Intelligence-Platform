-- Basket prices with the comparisons the dashboard headlines need: the same place a
-- month and a year earlier, and the national price that month. Joins on the month,
-- not on row order, because subnational series have gaps.
with prices as (
    select
        prices.month,
        prices.geo_code,
        -- The seed label: PSA spells it in different case across tables.
        geolocations.geolocation,
        prices.geo_level,
        geolocations.region_code,
        staples.staple,
        staples.category,
        staples.unit,
        prices.price,
        prices.released_at
    from {{ ref('int_retail_prices') }} as prices
    inner join {{ ref('staples') }} as staples
        on prices.commodity = staples.commodity
    left join {{ ref('geolocations') }} as geolocations
        on prices.geo_code = geolocations.geo_code
)

select
    prices.*,
    month_ago.price as price_month_ago,
    year_ago.price as price_year_ago,
    national.price as national_price,
    prices.price / month_ago.price - 1 as change_month,
    prices.price / year_ago.price - 1 as change_year,
    prices.price / national.price - 1 as vs_national
from prices
left join prices as month_ago
    on prices.geo_code = month_ago.geo_code
    and prices.staple = month_ago.staple
    and month_ago.month = prices.month - interval 1 month
left join prices as year_ago
    on prices.geo_code = year_ago.geo_code
    and prices.staple = year_ago.staple
    and year_ago.month = prices.month - interval 12 month
left join prices as national
    on national.geo_level = 'national'
    and prices.staple = national.staple
    and prices.month = national.month
