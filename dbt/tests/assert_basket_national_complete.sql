-- Every staple needs a national price every month, or its farmer's share and
-- verdict would quietly average over fewer months than its neighbours'.
with months as (
    select distinct month from {{ ref('int_retail_prices') }} where geo_level = 'national'
)

select months.month, staples.staple
from months
cross join {{ ref('staples') }} as staples
left join {{ ref('int_staple_prices') }} as prices
    on prices.geo_level = 'national'
    and prices.month = months.month
    and prices.staple = staples.staple
where prices.price is null
