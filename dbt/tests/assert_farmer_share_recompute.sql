-- Recompute every farmer's share straight from the staged farmgate prices and the
-- retail prices, independent of int_farmer_share and int_staple_prices.
with expected as (
    select
        retail.month,
        retail.geo_code,
        commodities.staple,
        (farmgate.price / commodities.retail_yield) / retail.price as share
    from {{ ref('farmgate_commodities') }} as commodities
    inner join {{ ref('staples') }} as staples on commodities.staple = staples.staple
    inner join {{ ref('stg_psa__farmgate_prices') }} as farmgate
        on commodities.table_id = farmgate.table_id
        and commodities.farmgate_commodity = farmgate.commodity
        and farmgate.snapshot_rank = 1
        and farmgate.price > 0
    inner join {{ ref('farmgate_geolocations') }} as labels
        on farmgate.geo_label = labels.label
    inner join {{ ref('int_retail_prices') }} as retail
        on staples.commodity = retail.commodity
        and labels.geo_code = retail.geo_code
        and farmgate.month = retail.month
    anti join {{ ref('farmer_share_exclusions') }} as exclusions
        on labels.geo_code = exclusions.geo_code
        and commodities.staple = exclusions.staple
)

select expected.*, model.farmer_share
from expected
full join {{ ref('int_farmer_share') }} as model
    on expected.month = model.month
    and expected.geo_code = model.geo_code
    and expected.staple = model.staple
where abs(coalesce(expected.share, -1) - coalesce(model.farmer_share, -2)) > 1e-9
