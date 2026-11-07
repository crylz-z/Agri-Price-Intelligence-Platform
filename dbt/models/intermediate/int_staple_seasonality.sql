-- The usual price swing of each staple by calendar month, nationally. Each month is
-- compared with the centred 13-month average around it, so a rising trend doesn't
-- read as "December is dear". Only months with 6 months of data on both sides count.
with national as (
    select
        staple,
        month,
        price,
        avg(price) over centred as centred_average,
        count(price) over centred as months_in_window
    from {{ ref('int_staple_prices') }}
    where geo_level = 'national'
    window centred as (
        partition by staple order by month rows between 6 preceding and 6 following
    )
)

select
    staple,
    month(month) as calendar_month,
    avg(price / centred_average - 1) as seasonal_index,
    count(*) as years
from national
where months_in_window = 13
group by all
