-- Every region's dish costs from 2024 have a minimum wage in force. Negros Island
-- Region (180000000) is left out: its wage board had issued no wage order by
-- NWPC's summary of 6 Oct 2026, so its dish wage share stays blank.
select distinct geo_code, geolocation, month
from {{ ref('int_dish_costs') }}
where geo_level = 'region'
    and month >= date '2024-01-01'
    and geo_code != '180000000'
    and daily_wage is null
