-- A farmgate commodity PSA renamed would otherwise drop out of the share silently.
select commodities.*
from {{ ref('farmgate_commodities') }} as commodities
where not exists (
    select 1
    from {{ ref('stg_psa__farmgate_prices') }} as prices
    where prices.snapshot_rank = 1
        and prices.table_id = commodities.table_id
        and prices.commodity = commodities.farmgate_commodity
)
