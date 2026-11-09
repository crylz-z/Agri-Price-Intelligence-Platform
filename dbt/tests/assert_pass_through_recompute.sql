-- Recompute up_pass_through and down_pass_through by a separate path (ADR 11):
-- the year-earlier month found with date_diff, not interval arithmetic, prices
-- deflated after the join, not before, and the middle's cut from store - farm.
with national as (
    select f.month, f.staple, f.farmgate_equivalent as farm, f.retail_price as store,
        c.cpi
    from {{ ref('int_farmer_share') }} as f
    inner join {{ ref('stg_psa__cpi') }} as c
        on f.month = c.month and c.commodity = '0 - ALL ITEMS'
    where f.geo_level = 'national'
),

pairs as (
    select a.staple,
        a.farm * 100 / a.cpi - b.farm * 100 / b.cpi as farm_move,
        a.store * 100 / a.cpi - b.store * 100 / b.cpi as store_move,
        (a.farm / a.cpi) / (b.farm / b.cpi) - 1 as farm_change
    from national as a
    inner join national as b
        on a.staple = b.staple and date_diff('month', b.month, a.month) = 12
),

expected as (
    select staple,
        sum(store_move) filter (where farm_change > {{ var('move_threshold') }})
            / sum(farm_move) filter (where farm_change > {{ var('move_threshold') }})
            as up_pass_through,
        sum(store_move) filter (where farm_change < -{{ var('move_threshold') }})
            / sum(farm_move) filter (where farm_change < -{{ var('move_threshold') }})
            as down_pass_through
    from pairs
    group by staple
)

select expected.*, model.up_pass_through as model_up, model.down_pass_through as model_down
from expected
inner join {{ ref('int_food_verdicts') }} as model on expected.staple = model.staple
where abs(coalesce(expected.up_pass_through, -9) - coalesce(model.up_pass_through, -9)) > 1e-9
    or abs(coalesce(expected.down_pass_through, -9) - coalesce(model.down_pass_through, -9)) > 1e-9
