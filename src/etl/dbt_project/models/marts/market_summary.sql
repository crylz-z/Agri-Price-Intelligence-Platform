
with daily_data as (
    select * from {{ ref('stg_market_prices') }}
)

select
    extract_ts::date as report_date,
    region_name,
    commodity_group,
    commodity_name,
    market_name,
    avg(price) as avg_price,
    min(price) as min_price,
    max(price) as max_price
from daily_data
group by 1, 2, 3, 4, 5
