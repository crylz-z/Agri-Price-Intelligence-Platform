-- Recompute the trader's and store's cuts straight from the staged wholesale
-- prices, independent of int_farmer_share's wholesale join (ADR 11), and check
-- that the two cuts add up to the whole gap. Fish rows are quarters: the mean of
-- the three months whose date_trunc quarter is the row's month.
with monthly as (
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
),

quarters as (
    select geo_code, staple, date_trunc('quarter', month) as month,
        sum(wholesale_price) / count(*) as wholesale_price
    from monthly
    group by all
    having count(*) = 3
),

expected as (
    select model.month, model.geo_code, model.staple,
        if(model.months_in_period = 3, quarters.wholesale_price, monthly.wholesale_price)
            as wholesale_price
    from {{ ref('int_farmer_share') }} as model
    left join monthly
        on model.month = monthly.month
        and model.geo_code = monthly.geo_code
        and model.staple = monthly.staple
    left join quarters
        on model.month = quarters.month
        and model.geo_code = quarters.geo_code
        and model.staple = quarters.staple
)

select model.month, model.geo_code, model.staple, model.wholesale_price,
    expected.wholesale_price as expected_wholesale
from {{ ref('int_farmer_share') }} as model
left join expected
    on model.month = expected.month
    and model.geo_code = expected.geo_code
    and model.staple = expected.staple
where (model.wholesale_price is null) != (expected.wholesale_price is null)
    or abs(model.wholesale_price - expected.wholesale_price) > 1e-9
    or abs(model.trader_cut - (expected.wholesale_price - model.farmgate_equivalent)) > 1e-9
    or abs(model.trader_cut + model.store_cut - model.peso_gap) > 1e-9
