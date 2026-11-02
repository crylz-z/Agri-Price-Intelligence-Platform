{{ config(location=lake_root() ~ '/mart/retail_prices_monthly.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_retail_prices') }}
order by month, geo_code, commodity
