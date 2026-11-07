select month, geo_code, dish, count(*) as n
from {{ ref('int_dish_costs') }}
group by all
having count(*) > 1
