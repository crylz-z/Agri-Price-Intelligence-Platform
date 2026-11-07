-- Recompute every national dish cost as sum(quantity x price) straight from the
-- retail prices, independent of int_dish_costs.
with sizes as (
    select dish, count(*) as lines from {{ ref('recipes') }} group by dish
),

expected as (
    select prices.month, recipes.dish, sum(recipes.quantity * prices.price) as cost
    from {{ ref('recipes') }} as recipes
    inner join {{ ref('staples') }} as staples on recipes.staple = staples.staple
    inner join {{ ref('int_retail_prices') }} as prices
        on staples.commodity = prices.commodity
        and prices.geo_level = 'national'
    inner join sizes on recipes.dish = sizes.dish
    group by prices.month, recipes.dish, sizes.lines
    having count(*) = sizes.lines
)

select expected.*, model.dish_cost
from expected
full join (
    select * from {{ ref('int_dish_costs') }} where geo_level = 'national'
) as model
    on expected.month = model.month and expected.dish = model.dish
where abs(coalesce(expected.cost, -1) - coalesce(model.dish_cost, -2)) > 1e-6
