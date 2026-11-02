select *
from {{ ref('int_retail_prices') }}
where price <= 0
