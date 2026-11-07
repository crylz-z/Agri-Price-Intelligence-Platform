select * from {{ ref('int_dish_costs') }} where dish_cost <= 0
