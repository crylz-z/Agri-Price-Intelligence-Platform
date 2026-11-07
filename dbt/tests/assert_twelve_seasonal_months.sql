select staple, count(*) as months, min(years) as fewest_years
from {{ ref('int_staple_seasonality') }}
group by staple
having count(*) <> 12 or min(years) < 5
