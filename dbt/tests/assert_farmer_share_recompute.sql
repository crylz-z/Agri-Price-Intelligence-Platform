-- Recompute every farmer's share straight from the staged farmgate prices and the
-- retail prices, independent of int_farmer_share and int_staple_prices. A fish
-- quarter's retail price is the mean of the retail months whose date_trunc
-- quarter is the farm row's month, all three of them.
with expected as (
    select
        farmgate.month,
        labels.geo_code,
        commodities.staple,
        (any_value(farmgate.price) / any_value(commodities.retail_yield))
            / (sum(retail.price) / count(*)) as share
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
        and if(farmgate.months_in_period = 3, date_trunc('quarter', retail.month),
            retail.month) = farmgate.month
    anti join {{ ref('farmer_share_exclusions') }} as exclusions
        on labels.geo_code = exclusions.geo_code
        and commodities.staple = exclusions.staple
    group by farmgate.month, labels.geo_code, commodities.staple
    having count(*) = any_value(farmgate.months_in_period)
)

select expected.*, model.farmer_share
from expected
full join {{ ref('int_farmer_share') }} as model
    on expected.month = model.month
    and expected.geo_code = model.geo_code
    and expected.staple = model.staple
where abs(coalesce(expected.share, -1) - coalesce(model.farmer_share, -2)) > 1e-9
