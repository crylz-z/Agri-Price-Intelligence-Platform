-- The latest snapshot's prices with geo codes and commodity groups. Every check
-- that must stop a bad publish runs on this model or upstream of it.
select
    prices.month,
    geolocations.geo_code,
    prices.geolocation,
    prices.geo_level,
    psa_tables.commodity_group,
    prices.commodity,
    prices.price,
    prices.released_at
from {{ ref('stg_psa__retail_prices') }} as prices
-- PSA spells the same geolocation in different case across tables.
left join {{ ref('geolocations') }} as geolocations
    on lower(prices.geolocation) = lower(geolocations.geolocation)
left join {{ ref('psa_tables') }} as psa_tables
    on prices.table_id = psa_tables.table_id
where prices.snapshot_rank = 1
    and prices.price is not null
