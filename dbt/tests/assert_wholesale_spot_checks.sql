-- National wholesale prices read off OpenSTAT with "format": "json", outside the
-- pipeline (ADR 11): red onion (0052M4AWB04) on 2026-11-08, bangus (0052M4AWB10)
-- on 2026-11-11.
with expected as (
    select * from (values
        ('Onion Red Creole (Bermuda Red)', date '2018-01-01', 84.86),
        ('Onion Red Creole (Bermuda Red)', date '2026-07-01', 79.70),
        ('Bangus [Milkfish]', date '2018-01-01', 129.23),
        ('Bangus [Milkfish]', date '2026-09-01', 172.12)
    ) as t(commodity, month, price)
)

select expected.commodity, expected.month, expected.price, staged.price as staged_price
from expected
left join {{ ref('stg_psa__wholesale_prices') }} as staged
    on expected.month = staged.month
    and staged.snapshot_rank = 1
    and staged.geo_level = 'national'
    and staged.commodity = expected.commodity
where staged.price is null or abs(staged.price - expected.price) > 1e-9
