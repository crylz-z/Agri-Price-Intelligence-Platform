-- The latest and previous snapshot of every wholesale table, national and region
-- rows only, one row per geolocation, commodity and month. Empty cells are kept
-- (price null). Same layout as the retail and most farmgate tables.
-- depends_on: {{ ref('psa_farmgate_tables') }}, {{ ref('psa_wholesale_tables') }}, {{ ref('psa_cpi_tables') }}
with snapshots as (
    select
        *,
        regexp_extract(filename, 'updated=(\w+)\.csv', 1) as updated
    from read_csv(
        [{%- for file in psa_snapshot_files(kind='wholesale', keep=2) %}'{{ file }}'{{ "," if not loop.last }}{% endfor -%}],
        header = true,
        all_varchar = true,
        union_by_name = true,
        hive_partitioning = true,
        filename = true,
        encoding = 'latin-1',  -- PSA sends Windows-1252
        nullstr = ['.', '..', '...']
    )
    -- PSA indents the label: no dots national, ".." region, "...." province.
    where length(Geolocation) - length(ltrim(Geolocation, '.')) <= 2
),

ranked as (
    select
        *,
        dense_rank() over (partition by "table" order by updated desc) as snapshot_rank
    from snapshots
),

cells as (
    select *
    from ranked
    unpivot include nulls (price for period in (columns('^\d{4} ')))
)

select
    "table" as table_id,
    strptime(updated, '%Y%m%dT%H%M%S') as released_at,
    snapshot_rank,
    ltrim(Geolocation, '.') as geolocation,
    -- The join key to seeds/farmgate_geolocations.csv (the same labels).
    lower(trim(regexp_replace(ltrim(Geolocation, '.'), '\s+\d+/$', ''))) as geo_label,
    if(Geolocation = ltrim(Geolocation, '.'), 'national', 'region') as geo_level,
    Commodity as commodity,
    strptime(period, '%Y %B')::date as month,
    cast(price as double) as price
from cells
where period not like '% Annual'
