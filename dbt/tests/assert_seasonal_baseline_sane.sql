-- The usual range is ordered, each food has at most one row per calendar month,
-- and every band rests on at least 5 past years.
select staple, calendar_month, 'low > median > high order broken' as problem
from {{ ref('int_seasonal_baseline') }}
where not (ratio_low <= ratio_median and ratio_median <= ratio_high)

union all

select staple, calendar_month, 'duplicate food and month'
from {{ ref('int_seasonal_baseline') }}
group by all
having count(*) > 1

union all

select staple, null, 'more than 12 months'
from {{ ref('int_seasonal_baseline') }}
group by staple
having count(*) > 12

union all

select staple, calendar_month, 'month outside 1-12 or under 5 years'
from {{ ref('int_seasonal_baseline') }}
where calendar_month not between 1 and 12 or years_used < 5
