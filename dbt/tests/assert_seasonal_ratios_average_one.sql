-- Each full past year's 12 ratios average to 1, or the index is not its own year's.
select staple, year, count(*) as months, avg(ratio) as mean_ratio
from {{ ref('int_seasonal_index') }}
group by all
having count(*) <> 12 or abs(avg(ratio) - 1) > 1e-9
