{{ config(severity='warn') }}

-- National prices average many markets, so a month-to-month move over 2x is more
-- likely a PSA data error than a real change. Regions and provinces are too
-- volatile for this check (hundreds of such moves since 2018).
with national as (
    select
        commodity,
        month,
        price,
        lag(price) over (partition by commodity order by month) as previous_price
    from {{ ref('int_retail_prices') }}
    where geo_level = 'national'
)

select *
from national
where price > 2 * previous_price
    or price < previous_price / 2
