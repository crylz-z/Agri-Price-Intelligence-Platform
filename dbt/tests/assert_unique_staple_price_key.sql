select month, geo_code, staple, count(*) as n
from {{ ref('int_staple_prices') }}
group by all
having count(*) > 1
