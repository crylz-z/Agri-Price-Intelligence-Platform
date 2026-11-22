-- Prices fetched straight from OpenSTAT's JSON API (not our CSV ingest) must match
-- the model to the centavo. A failure is a parsing or mapping bug, or a PSA
-- revision: check OpenSTAT, then fix the code or refresh the seed.
select checks.*, prices.price as model_price
from {{ ref('psa_spot_checks') }} as checks
left join {{ ref('int_retail_prices') }} as prices
    on checks.geo_code = prices.geo_code
    and checks.commodity = prices.commodity
    and checks.month = prices.month
where prices.price is null or abs(prices.price - checks.price) > 0.005
