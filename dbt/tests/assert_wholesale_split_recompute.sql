-- Recompute the trader's and store's cuts straight from the staged wholesale
-- prices, independent of int_farmer_share's wholesale join (ADR 11), and check
-- that the two cuts add up to the whole gap.
with expected as (
    select
        labels.geo_code,
        commodities.staple,
        prices.month,
        prices.price as wholesale_price
    from {{ ref('wholesale_commodities') }} as commodities
    inner join {{ ref('stg_psa__wholesale_prices') }} as prices
        on commodities.table_id = prices.table_id
        and commodities.wholesale_commodity = prices.commodity
        and prices.snapshot_rank = 1
        and prices.price > 0
    inner join {{ ref('farmgate_geolocations') }} as labels
        on prices.geo_label = labels.label
)

select model.month, model.geo_code, model.staple, model.wholesale_price,
    expected.wholesale_price as expected_wholesale
from {{ ref('int_farmer_share') }} as model
left join expected
    on model.month = expected.month
    and model.geo_code = expected.geo_code
    and model.staple = expected.staple
where model.wholesale_price is distinct from expected.wholesale_price
    or abs(model.trader_cut - (expected.wholesale_price - model.farmgate_equivalent)) > 1e-9
    or abs(model.trader_cut + model.store_cut - model.peso_gap) > 1e-9
