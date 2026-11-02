-- Every table's latest snapshot lists all of PSA's geolocations.
select psa_tables.table_id, geolocations.geo_code, geolocations.geolocation
from {{ ref('psa_tables') }} as psa_tables
cross join {{ ref('geolocations') }} as geolocations
where not exists (
    select 1
    from {{ ref('stg_psa__retail_prices') }} as prices
    where prices.snapshot_rank = 1
        and prices.table_id = psa_tables.table_id
        and lower(prices.geolocation) = lower(geolocations.geolocation)
)
