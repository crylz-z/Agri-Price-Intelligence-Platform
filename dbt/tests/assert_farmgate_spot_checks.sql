-- Farmgate prices fetched straight from OpenSTAT's JSON API (not our CSV ingest)
-- must match the staged price to the centavo. A failure is a parsing or mapping
-- bug, or a PSA revision: check OpenSTAT, then fix the code or refresh the seed.
-- A geo code can have two labels (the fish table spells "Nothern Mindanao").
select checks.*
from {{ ref('psa_farmgate_spot_checks') }} as checks
where not exists (
    select 1
    from {{ ref('farmgate_geolocations') }} as labels
    inner join {{ ref('stg_psa__farmgate_prices') }} as prices
        on labels.label = prices.geo_label
    where labels.geo_code = checks.geo_code
        and prices.table_id = checks.table_id
        and prices.commodity = checks.commodity
        and prices.month = checks.month
        and prices.snapshot_rank = 1
        and abs(prices.price - checks.price) <= 0.005
)
