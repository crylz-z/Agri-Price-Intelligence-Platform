-- Recompute each year-on-year change from the retail prices by date arithmetic,
-- independent of the self-joins in int_staple_prices.
with expected as (
    select
        now.geo_code,
        staples.staple,
        now.month,
        now.price / earlier.price - 1 as change_year
    from {{ ref('int_retail_prices') }} as now
    inner join {{ ref('staples') }} as staples on now.commodity = staples.commodity
    inner join {{ ref('int_retail_prices') }} as earlier
        on now.geo_code = earlier.geo_code
        and now.commodity = earlier.commodity
        and date_diff('month', earlier.month, now.month) = 12
)

select expected.*, model.change_year as model_change_year
from expected
full join {{ ref('int_staple_prices') }} as model
    on expected.geo_code = model.geo_code
    and expected.staple = model.staple
    and expected.month = model.month
where (expected.change_year is not null or model.change_year is not null)
    and abs(coalesce(expected.change_year, 99) - coalesce(model.change_year, -99))
        > 1e-9
