-- A table PSA stopped publishing (or renamed) is a dimension change.
select table_id
from {{ ref('psa_tables') }}
where table_id not in (
    select table_id from {{ ref('stg_psa__retail_prices') }} where snapshot_rank = 1
)
