-- A national or region label PSA renames would otherwise drop out of the share
-- silently: add it to seeds/farmgate_geolocations.csv.
select distinct table_id, geolocation, geo_label
from {{ ref('stg_psa__farmgate_prices') }}
where snapshot_rank = 1
    and geo_label not in (select label from {{ ref('farmgate_geolocations') }})
