-- middle_change divides by the 2018 middle's cut, so it must be above zero.
select staple, middle_then
from {{ ref('int_food_verdicts') }}
where middle_then <= 0
