-- Recompute each food's year-on-year farm and store change by a separate path
-- (ADR 11): months a year apart found with date_diff, not interval arithmetic,
-- and the change as (now - earlier) / earlier, not now / earlier - 1.
with national as (
    select month, staple, months_in_period, farmgate_equivalent as farm,
        retail_price as store
    from {{ ref('int_farmer_share') }}
    where geo_level = 'national'
),

-- Monthly foods and fish (quarterly) each have their own latest period.
latest as (
    select months_in_period, max(month) as last_month from national group by all
),

expected as (
    select now.staple,
        (now.farm - earlier.farm) / earlier.farm as farm_change,
        (now.store - earlier.store) / earlier.store as store_change
    from national as now
    inner join latest
        on now.month = latest.last_month
        and now.months_in_period = latest.months_in_period
    inner join national as earlier
        on now.staple = earlier.staple
        and date_diff('month', earlier.month, now.month) = 12
),

model as (
    select * from {{ ref('int_price_changes') }} where farm_measure is null
)

select expected.staple, model.staple as model_staple
from expected
full join model on expected.staple = model.staple
where expected.staple is null
    or model.staple is null
    or abs(expected.farm_change - model.farm_change) > 1e-9
    or abs(expected.store_change - model.store_change) > 1e-9
