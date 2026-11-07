-- What one recipe costs per geolocation and month. A dish cost is left blank when
-- any of its staples has no price there that month: filling the gap from another
-- area would publish a number PSA never reported.
with places as (
    select distinct month, geo_code, geolocation, geo_level, region_code
    from {{ ref('int_staple_prices') }}
),

lines as (
    select
        places.*,
        recipes.dish,
        recipes.staple,
        recipes.quantity * staple_prices.price as line_cost
    from places
    cross join {{ ref('recipes') }} as recipes
    left join {{ ref('int_staple_prices') }} as staple_prices
        on places.month = staple_prices.month
        and places.geo_code = staple_prices.geo_code
        and recipes.staple = staple_prices.staple
),

dishes as (
    select
        month,
        geo_code,
        geolocation,
        geo_level,
        region_code,
        dish,
        if(count(line_cost) = count(*), sum(line_cost), null) as dish_cost,
        string_agg(staple, ', ' order by staple) filter (where line_cost is null)
            as missing_staples
    from lines
    group by all
)

select
    dishes.*,
    year_ago.dish_cost as dish_cost_year_ago,
    national.dish_cost as national_dish_cost,
    dishes.dish_cost / year_ago.dish_cost - 1 as change_year,
    dishes.dish_cost / national.dish_cost - 1 as vs_national
from dishes
left join dishes as year_ago
    on dishes.geo_code = year_ago.geo_code
    and dishes.dish = year_ago.dish
    and year_ago.month = dishes.month - interval 12 month
left join dishes as national
    on national.geo_level = 'national'
    and dishes.dish = national.dish
    and dishes.month = national.month
