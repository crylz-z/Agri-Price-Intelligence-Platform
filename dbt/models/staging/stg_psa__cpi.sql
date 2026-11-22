-- PSA's consumer price index (2018=100), national: one row per group and month.
-- Ingest asks OpenSTAT for the groups in CPI_GROUPS only (all items, transport,
-- diesel, electricity and fuels); a test checks that they are still those rows.
-- depends_on: {{ ref('psa_farmgate_tables') }}, {{ ref('psa_wholesale_tables') }}, {{ ref('psa_cpi_tables') }}
with snapshot as (
    select *
    from read_csv(
        [{%- for file in psa_snapshot_files(kind='cpi', keep=1) %}'{{ file }}'{{ "," if not loop.last }}{% endfor -%}],
        header = true,
        all_varchar = true,
        hive_partitioning = true,
        filename = true,
        encoding = 'latin-1',  -- PSA sends Windows-1252
        nullstr = ['.', '..', '...']
    )
),

cells as (
    select *
    from snapshot
    unpivot (cpi for period in (columns('^\d{4} ')))
)

select
    "table" as table_id,
    strptime(regexp_extract(filename, 'updated=(\w+)\.csv', 1), '%Y%m%dT%H%M%S')
        as released_at,
    Geolocation as geolocation,
    "Commodity Description" as commodity,
    -- "2018 Jan"; PSA also adds a yearly average column, "2018 Ave".
    strptime(period, '%Y %b')::date as month,
    cast(cpi as double) as cpi
from cells
where period not like '% Ave'
