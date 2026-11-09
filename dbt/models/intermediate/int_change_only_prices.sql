-- The foods in seeds/change_only_commodities by month, national: a farm price for
-- another product than the store's (a live hog against a pork cut), so only their
-- percent changes compare, never their pesos or a farmer's share.
select farm.month, seeds.staple, farm.price as farm, store.price as store,
    seeds.farm_measure
from {{ ref('stg_psa__farmgate_prices') }} as farm
inner join {{ ref('change_only_commodities') }} as seeds
    on farm.table_id = seeds.table_id
    and farm.commodity = seeds.farmgate_commodity
inner join {{ ref('int_staple_prices') }} as store
    on store.staple = seeds.staple
    and store.month = farm.month
    and store.geo_level = 'national'
where farm.snapshot_rank = 1
    and farm.geo_level = 'national'
    -- PSA fills farmgate cells with no sales with 0.00, not "..".
    and farm.price > 0
