-- A new release normally adds a month and revises a few, so far fewer filled
-- cells than the previous snapshot means a broken or partial release.
with filled as (
    select
        table_id,
        count(price) filter (where snapshot_rank = 1) as latest,
        count(price) filter (where snapshot_rank = 2) as previous
    from {{ ref('stg_psa__retail_prices') }}
    group by table_id
)

select *
from filled
where previous > 0
    and latest < 0.9 * previous
