-- One row per food and calendar month, national: the usual store price for that
-- time of year, in today's pesos. "Usual" is the range of past years' ratios
-- after dropping the highest and the lowest year, so one crisis year can't stretch
-- it. Today's pesos = ratio x the average store price over the 12 months before
-- the latest month (the month being judged doesn't set its own band). A month
-- needs at least 5 full past years. recent_* is the store price in that calendar
-- month within the 12 months ending at the latest month, for the chart's line.
with ranked as (
    select
        staple,
        calendar_month,
        ratio,
        row_number() over (partition by staple, calendar_month order by ratio) as rank_up,
        count(*) over (partition by staple, calendar_month) as years_used
    from {{ ref('int_seasonal_index') }}
),

months as (
    select
        staple,
        calendar_month,
        any_value(years_used) as years_used,
        median(ratio) as ratio_median,
        min(ratio) filter (where rank_up > 1 and rank_up < years_used) as ratio_low,
        max(ratio) filter (where rank_up > 1 and rank_up < years_used) as ratio_high
    from ranked
    group by all
    having any_value(years_used) >= 5
),

swing as (
    select staple, max(ratio_median) - min(ratio_median) as swing
    from months
    group by staple
),

national as (
    select month, staple, unit, price
    from {{ ref('int_staple_prices') }}
    where geo_level = 'national'
),

latest as (
    select staple, max(month) as latest_month
    from national
    group by staple
),

price_levels as (
    -- Null unless all 12 months before the latest one have a price.
    select
        latest.staple,
        latest.latest_month,
        if(count(national.price) = 12, avg(national.price), null) as price_level
    from latest
    left join national
        on national.staple = latest.staple
        and national.month between latest.latest_month - interval 12 month
        and latest.latest_month - interval 1 month
    group by all
),

recent as (
    select national.staple, national.unit, national.month, national.price
    from national
    inner join latest on national.staple = latest.staple
    where national.month > latest.latest_month - interval 12 month
)

select
    months.staple,
    months.calendar_month,
    months.years_used,
    months.ratio_low,
    months.ratio_median,
    months.ratio_high,
    swing.swing,
    price_levels.price_level,
    months.ratio_low * price_levels.price_level as usual_low,
    months.ratio_median * price_levels.price_level as usual_median,
    months.ratio_high * price_levels.price_level as usual_high,
    price_levels.latest_month,
    recent.month as recent_month,
    recent.price as recent_price,
    recent.unit
from months
inner join swing on months.staple = swing.staple
inner join price_levels on months.staple = price_levels.staple
left join recent
    on months.staple = recent.staple
    and months.calendar_month = month(recent.month)
