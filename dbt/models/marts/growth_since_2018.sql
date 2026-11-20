{{ config(location=lake_root() ~ '/mart/growth_since_2018.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_growth_since_2018') }}
order by store_change - farm_change desc
