-- Ingest picks the CPI rows by value code (CPI_GROUPS in src/etl/ingest.py); if
-- PSA reorders its codes, the snapshot holds other places or groups, and this
-- fails before any mart is built. Also: one row per group and month.
with expected as (
    select * from (values
        ('0 - ALL ITEMS'),
        ('04.5 - ELECTRICITY, GAS AND OTHER FUELS'),
        ('07 - TRANSPORT'),
        ('07.2.2.1 - Diesel (ND)')
    ) as t(commodity)
),

staged as (
    select geolocation, commodity, count(*) as rows, count(distinct month) as months
    from {{ ref('stg_psa__cpi') }}
    group by geolocation, commodity
)

select coalesce(staged.commodity, expected.commodity) as commodity, staged.geolocation
from staged
full join expected on staged.commodity = expected.commodity
where staged.commodity is null
    or expected.commodity is null
    or staged.geolocation <> 'PHILIPPINES'
    or staged.rows <> staged.months
