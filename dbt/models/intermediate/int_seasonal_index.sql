-- Each national store price as a ratio to its own calendar year's average, for
-- full past years only (12 months, before the food's latest year). Dividing by the
-- year's own average takes out general inflation and leaves the season's shape.
with national as (
    select month, staple, price
    from {{ ref('int_staple_prices') }}
    where geo_level = 'national'
),

latest as (
    select staple, max(month) as latest_month
    from national
    group by staple
),

full_years as (
    select national.staple, year(national.month) as year
    from national
    inner join latest on national.staple = latest.staple
    where year(national.month) < year(latest.latest_month)
    group by all
    having count(*) = 12
)

select
    national.staple,
    full_years.year,
    month(national.month) as calendar_month,
    national.price,
    national.price / avg(national.price) over (partition by national.staple, full_years.year)
        as ratio
from national
inner join full_years
    on national.staple = full_years.staple
    and year(national.month) = full_years.year
