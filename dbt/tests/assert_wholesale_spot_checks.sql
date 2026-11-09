-- National red onion wholesale prices read off OpenSTAT 0052M4AWB04 with
-- "format": "json" on 2026-11-08, outside the pipeline (ADR 11).
with expected as (
    select * from (values
        (date '2018-01-01', 84.86),
        (date '2026-07-01', 79.70)
    ) as t(month, price)
)

select expected.month, expected.price, staged.price as staged_price
from expected
left join {{ ref('stg_psa__wholesale_prices') }} as staged
    on expected.month = staged.month
    and staged.snapshot_rank = 1
    and staged.geo_level = 'national'
    and staged.commodity = 'Onion Red Creole (Bermuda Red)'
where staged.price is null or abs(staged.price - expected.price) > 1e-9
