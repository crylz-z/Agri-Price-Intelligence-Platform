-- Recompute each staple's middle's cut change, CPI change and verdict by a separate
-- path (ADR 11): months counted back from the latest with date_diff, not
-- interval arithmetic, and the middle's cut as store minus farm, not peso_gap.
with national as (
    select month, staple, retail_price - farmgate_equivalent as middle
    from {{ ref('int_farmer_share') }}
    where geo_level = 'national'
),

latest as (select max(month) as last_month from national),

spans as (
    select national.*,
        year(month) = 2018 as is_then,
        date_diff('month', month, last_month) between 0 and 11 as is_now
    from national cross join latest
),

cuts as (
    select staple,
        sum(middle) filter (where is_now) / count(*) filter (where is_now)
            / (sum(middle) filter (where is_then) / count(*) filter (where is_then))
            - 1 as middle_change
    from spans
    group by staple
    having count(*) filter (where is_then) > 0 and count(*) filter (where is_now) > 0
),

cpi as (
    select
        avg(cpi) filter (where date_diff('month', month, last_month) between 0 and 11)
            / avg(cpi) filter (where year(month) = 2018) - 1 as cpi_change
    from {{ ref('stg_psa__cpi') }} cross join latest
    where commodity = '0 - ALL ITEMS'
),

expected as (
    select cuts.staple, cuts.middle_change, cpi.cpi_change,
        case when cuts.middle_change > cpi.cpi_change + {{ var('verdict_margin') }}
            then 'suspicious' else 'cleared' end as verdict
    from cuts cross join cpi
)

select expected.*, model.middle_change as model_middle, model.verdict as model_verdict
from expected
full join {{ ref('int_food_verdicts') }} as model on expected.staple = model.staple
where abs(coalesce(expected.middle_change, -9) - coalesce(model.middle_change, -8)) > 1e-9
    or abs(coalesce(expected.cpi_change, -9) - coalesce(model.cpi_change, -8)) > 1e-9
    or expected.verdict is distinct from model.verdict
