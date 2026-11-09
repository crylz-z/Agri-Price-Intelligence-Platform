-- One row per staple, national: farm, store and middle's cut averaged over 2018
-- ("then") and over the 12 months to the latest month with both prices ("now"),
-- against inflation (CPI) over the same months. A staple is suspicious when its
-- middle's cut grew faster than CPI by more than var('verdict_margin') points.
-- Diesel, transport and fuel CPI over the same months answer "is the gap just
-- fuel costs?".
with national as (
    select month, staple, category, unit,
        farmgate_equivalent as farm, retail_price as store, peso_gap as middle,
        trader_cut, store_cut
    from {{ ref('int_farmer_share') }}
    where geo_level = 'national'
),

windows as (
    select
        date '2018-01-01' as then_start,
        date '2018-12-01' as then_end,
        max(month) - interval 11 month as now_start,
        max(month) as now_end
    from national
),

tagged as (
    select
        national.*,
        case
            when national.month between windows.then_start and windows.then_end then 'then'
            when national.month between windows.now_start and windows.now_end then 'now'
        end as span
    from national cross join windows
),

cpi_groups as (
    select
        cpi.commodity,
        avg(cpi.cpi) filter (where cpi.month between windows.then_start and windows.then_end)
            as cpi_then,
        avg(cpi.cpi) filter (where cpi.month between windows.now_start and windows.now_end)
            as cpi_now
    from {{ ref('stg_psa__cpi') }} as cpi cross join windows
    group by cpi.commodity
),

cpi as (
    select
        any_value(cpi_then) filter (where commodity = '0 - ALL ITEMS') as cpi_then,
        any_value(cpi_now) filter (where commodity = '0 - ALL ITEMS') as cpi_now,
        any_value(cpi_now / cpi_then - 1) filter (where commodity = '07.2.2.1 - Diesel (ND)')
            as diesel_change,
        any_value(cpi_now / cpi_then - 1) filter (where commodity = '07 - TRANSPORT')
            as transport_change,
        any_value(cpi_now / cpi_then - 1)
            filter (where commodity = '04.5 - ELECTRICITY, GAS AND OTHER FUELS')
            as fuel_change
    from cpi_groups
),

averages as (
    select
        staple,
        any_value(category) as category,
        any_value(unit) as unit,
        count(*) filter (where span = 'then') as then_months,
        count(*) filter (where span = 'now') as now_months,
        avg(farm) filter (where span = 'then') as farm_then,
        avg(farm) filter (where span = 'now') as farm_now,
        avg(store) filter (where span = 'then') as store_then,
        avg(store) filter (where span = 'now') as store_now,
        avg(middle) filter (where span = 'then') as middle_then,
        avg(middle) filter (where span = 'now') as middle_now,
        -- Traders' and stores' pesos of every ₱100 the shopper paid, over the
        -- months with a wholesale price (none for kangkong). Pesos, not a
        -- percent change: a trader's cut can average below ₱0 (ginger, 2018).
        sum(trader_cut) filter (where span = 'then' and trader_cut is not null)
            / sum(store) filter (where span = 'then' and trader_cut is not null)
            * 100 as trader_part_then,
        sum(trader_cut) filter (where span = 'now' and trader_cut is not null)
            / sum(store) filter (where span = 'now' and trader_cut is not null)
            * 100 as trader_part_now,
        sum(store_cut) filter (where span = 'then' and store_cut is not null)
            / sum(store) filter (where span = 'then' and store_cut is not null)
            * 100 as store_part_then,
        sum(store_cut) filter (where span = 'now' and store_cut is not null)
            / sum(store) filter (where span = 'now' and store_cut is not null)
            * 100 as store_part_now
    from tagged
    group by staple
),

-- Up fast, down slow: in each month whose farm price moved over 15% from a year
-- earlier, how many pesos the store price moved per peso the farm price moved.
-- Both prices are in 2018 pesos (divided by CPI), so general inflation does not
-- lift the "up" figure or shrink the "down" one. 1 means the store moved peso for
-- peso; below 1 on the way down means shoppers kept paying for a fall they never
-- saw. Months overlap, so these are evidence, not a test of significance.
real_prices as (
    select national.staple, national.month,
        national.farm / cpi.cpi * 100 as farm,
        national.store / cpi.cpi * 100 as store
    from national
    inner join {{ ref('stg_psa__cpi') }} as cpi
        on national.month = cpi.month and cpi.commodity = '0 - ALL ITEMS'
),

moves as (
    select
        current.staple,
        current.farm - earlier.farm as farm_move,
        current.store - earlier.store as store_move,
        case
            when current.farm / earlier.farm - 1 > {{ var('move_threshold') }} then 'up'
            when current.farm / earlier.farm - 1 < -{{ var('move_threshold') }} then 'down'
        end as direction
    from real_prices as current
    inner join real_prices as earlier
        on current.staple = earlier.staple
        and earlier.month = current.month - interval 12 month
),

pass_through as (
    select
        staple,
        count(*) filter (where direction = 'up') as up_months,
        sum(store_move) filter (where direction = 'up')
            / sum(farm_move) filter (where direction = 'up') as up_pass_through,
        count(*) filter (where direction = 'down') as down_months,
        sum(store_move) filter (where direction = 'down')
            / sum(farm_move) filter (where direction = 'down') as down_pass_through
    from moves
    group by staple
)

select
    averages.staple,
    averages.category,
    averages.unit,
    windows.then_start,
    windows.then_end,
    windows.now_start,
    windows.now_end,
    averages.then_months,
    averages.now_months,
    averages.farm_then,
    averages.farm_now,
    averages.store_then,
    averages.store_now,
    averages.middle_then,
    averages.middle_now,
    averages.trader_part_then,
    averages.trader_part_now,
    averages.store_part_then,
    averages.store_part_now,
    averages.farm_now / averages.farm_then - 1 as farm_change,
    averages.store_now / averages.store_then - 1 as store_change,
    averages.middle_now / averages.middle_then - 1 as middle_change,
    cpi.cpi_then,
    cpi.cpi_now,
    cpi.cpi_now / cpi.cpi_then - 1 as cpi_change,
    cpi.diesel_change,
    cpi.transport_change,
    cpi.fuel_change,
    coalesce(pass_through.up_months, 0) as up_months,
    pass_through.up_pass_through,
    coalesce(pass_through.down_months, 0) as down_months,
    pass_through.down_pass_through,
    if(
        averages.middle_now / averages.middle_then - 1
            > cpi.cpi_now / cpi.cpi_then - 1 + {{ var('verdict_margin') }},
        'suspicious', 'cleared'
    ) as verdict
from averages
cross join windows
cross join cpi
left join pass_through on averages.staple = pass_through.staple
where averages.then_months > 0 and averages.now_months > 0
