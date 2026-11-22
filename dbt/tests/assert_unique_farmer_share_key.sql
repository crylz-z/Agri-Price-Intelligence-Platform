select month, geo_code, staple, count(*) as n
from {{ ref('int_farmer_share') }}
group by all
having count(*) > 1
