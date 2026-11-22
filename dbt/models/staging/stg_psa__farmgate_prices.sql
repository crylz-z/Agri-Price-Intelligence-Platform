-- The latest and previous snapshot of every farmgate table, national and region
-- rows only (the farmer's share has no provinces), one row per geolocation,
-- commodity and period. Empty cells are kept (price null). Most tables are
-- monthly; fish (0152M4GFPF0) is quarterly, so its row's month is the quarter's
-- first and months_in_period is 3.
-- depends_on: {{ ref('psa_farmgate_tables') }}, {{ ref('psa_wholesale_tables') }}, {{ ref('psa_cpi_tables') }}
with snapshots as (
    select
        *,
        regexp_extract(filename, 'updated=(\w+)\.csv', 1) as updated
    from read_csv(
        [{%- for file in psa_snapshot_files(kind='farmgate', keep=2) %}'{{ file }}'{{ "," if not loop.last }}{% endfor -%}],
        header = true,
        all_varchar = true,
        union_by_name = true,
        hive_partitioning = true,
        filename = true,
        encoding = 'latin-1',  -- PSA sends Windows-1252
        -- AFN11 also marks a month not yet released "..."
        nullstr = ['.', '..', '...']
    )
    -- PSA indents the label: no dots national, ".." region. Province rows carry
    -- footnote marks in price cells ("1/"), so they are dropped before the cast.
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
    -- The join key to seeds/farmgate_geolocations.csv: lower case, without the
    -- trailing footnote mark some tables add ("NEGROS ISLAND REGION 1/").
    lower(trim(regexp_replace(ltrim(Geolocation, '.'), '\s+\d+/$', ''))) as geo_label,
    if(Geolocation = ltrim(Geolocation, '.'), 'national', 'region') as geo_level,
    -- AFN11 (livestock and eggs) calls the commodity column "Type", and fish
    -- "Species", indented under ALL SPECIES ("..Milkfish").
    coalesce(Commodity, "Type", ltrim(Species, '.')) as commodity,
    -- "2018 January", or for fish "2018 Quarter 3" (July to September).
    coalesce(
        try_strptime(period, '%Y %B')::date,
        make_date(
            cast(left(period, 4) as integer),
            cast(right(period, 1) as integer) * 3 - 2,
            1
        )
    ) as month,
    if(period like '% Quarter %', 3, 1) as months_in_period,
    cast(price as double) as price
from cells
where period not like '% Annual'
    -- union_by_name gives every table every period column: keep each table's own,
    -- quarters for the fish table (the only one with a Species column), months
    -- for the rest.
    and (period like '% Quarter %') = (Species is not null)
