-- The latest and previous snapshot of every table, one row per geolocation,
-- commodity and month. Empty cells are kept (price null) so tests can compare
-- snapshots and see every geolocation.
with snapshots as (
    select
        *,
        regexp_extract(filename, 'updated=(\w+)\.csv', 1) as updated
    from read_csv(
        [{%- for file in psa_snapshot_files(keep=2) %}'{{ file }}'{{ "," if not loop.last }}{% endfor -%}],
        header = true,
        all_varchar = true,
        union_by_name = true,
        hive_partitioning = true,
        filename = true,
        encoding = 'latin-1',  -- PSA sends Windows-1252
        nullstr = ['.', '..']
    )
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
    -- PSA indents the label: no dots national, ".." region, "...." province or city.
    ltrim(Geolocation, '.') as geolocation,
    case length(Geolocation) - length(ltrim(Geolocation, '.'))
        when 0 then 'national'
        when 2 then 'region'
        when 4 then 'province'
    end as geo_level,
    Commodity as commodity,
    strptime(period, '%Y %B')::date as month,
    cast(price as double) as price
from cells
where period not like '% Annual'
