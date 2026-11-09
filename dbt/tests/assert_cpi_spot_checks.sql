-- CPI values read off OpenSTAT 0012M4ACP22 on 2026-11-08, outside the pipeline
-- (ADR 11). July 2026's 135.6 is also PSA's published headline.
with expected as (
    select * from (values
        ('0 - ALL ITEMS', date '2018-01-01', 97.2),
        ('0 - ALL ITEMS', date '2026-07-01', 135.6),
        ('07.2.2.1 - Diesel (ND)', date '2018-01-01', 87.9705063563373),
        ('07.2.2.1 - Diesel (ND)', date '2026-07-01', 186.184931896786)
    ) as t(commodity, month, cpi)
)

select expected.commodity, expected.month, expected.cpi, staged.cpi as staged_cpi
from expected
left join {{ ref('stg_psa__cpi') }} as staged
    on expected.month = staged.month and expected.commodity = staged.commodity
where staged.cpi is null or abs(staged.cpi - expected.cpi) > 1e-9
