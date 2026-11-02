select month, geo_code, commodity, count(*) as n
from {{ ref('int_retail_prices') }}
group by all
having count(*) > 1
