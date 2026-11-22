-- Recompute each food's growth since 2018 by a separate path (ADR 11): foods with
-- a farmer's share must equal int_food_verdicts' farm_change and store_change,
-- and the change-only foods are recomputed from int_change_only_prices with
-- months counted back by date_diff and growth as (now - then) / then.
with latest as (
    select max(month) as last_month
    from {{ ref('int_farmer_share') }}
    where geo_level = 'national'
),

meat as (
    select staple,
        (sum(farm) filter (where date_diff('month', month, last_month) between 0 and 11)
            / count(*) filter (where date_diff('month', month, last_month) between 0 and 11)
          - sum(farm) filter (where year(month) = 2018)
            / count(*) filter (where year(month) = 2018))
          / (sum(farm) filter (where year(month) = 2018)
            / count(*) filter (where year(month) = 2018)) as farm_change,
        (sum(store) filter (where date_diff('month', month, last_month) between 0 and 11)
            / count(*) filter (where date_diff('month', month, last_month) between 0 and 11)
          - sum(store) filter (where year(month) = 2018)
            / count(*) filter (where year(month) = 2018))
          / (sum(store) filter (where year(month) = 2018)
            / count(*) filter (where year(month) = 2018)) as store_change
    from {{ ref('int_change_only_prices') }} cross join latest
    group by staple
),

expected as (
    select staple, farm_change, store_change from {{ ref('int_food_verdicts') }}
    union all
    select staple, farm_change, store_change from meat
)

select expected.staple, model.staple as model_staple
from expected
full join {{ ref('int_growth_since_2018') }} as model on expected.staple = model.staple
where expected.staple is null
    or model.staple is null
    or abs(expected.farm_change - model.farm_change) > 1e-9
    or abs(expected.store_change - model.store_change) > 1e-9
