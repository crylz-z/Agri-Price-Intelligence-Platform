{{ config(location=lake_root() ~ '/mart/staple_prices_monthly.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_staple_prices') }}
order by month, geo_code, staple
