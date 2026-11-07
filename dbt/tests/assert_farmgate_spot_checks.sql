-- Farmgate prices fetched straight from OpenSTAT's JSON API (not our CSV ingest)
-- must match the staged price to the centavo. A failure is a parsing or mapping
-- bug, or a PSA revision: check OpenSTAT, then fix the code or refresh the seed.
select checks.*, prices.price as model_price
from {{ ref('psa_farmgate_spot_checks') }} as checks
left join {{ ref('farmgate_geolocations') }} as labels
    on checks.geo_code = labels.geo_code
left join {{ ref('stg_psa__farmgate_prices') }} as prices
    on checks.table_id = prices.table_id
    and checks.commodity = prices.commodity
    and checks.month = prices.month
    and labels.label = prices.geo_label
    and prices.snapshot_rank = 1
where prices.price is null or abs(prices.price - checks.price) > 0.005
