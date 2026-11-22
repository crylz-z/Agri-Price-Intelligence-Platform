-- A wholesale commodity or region label PSA renames would otherwise drop out of
-- the split silently: fix seeds/wholesale_commodities.csv or
-- seeds/farmgate_geolocations.csv. Every wholesale table has a mapped commodity,
-- so this also catches a table PSA stopped publishing.
select 'commodity' as missing, commodities.table_id, commodities.wholesale_commodity as label
from {{ ref('wholesale_commodities') }} as commodities
where not exists (
    select 1
    from {{ ref('stg_psa__wholesale_prices') }} as prices
    where prices.snapshot_rank = 1
        and prices.table_id = commodities.table_id
        and prices.commodity = commodities.wholesale_commodity
)

union all

select distinct 'geolocation', table_id, geolocation
from {{ ref('stg_psa__wholesale_prices') }}
where snapshot_rank = 1
    and geo_label not in (select label from {{ ref('farmgate_geolocations') }})
