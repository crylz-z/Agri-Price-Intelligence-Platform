{{ config(severity='warn') }}

-- PSA publishes about a month late; more than 3 months means it has stalled.
select max(month) as latest_month
from {{ ref('int_retail_prices') }}
having max(month) < date_trunc('month', current_date) - interval 3 month
