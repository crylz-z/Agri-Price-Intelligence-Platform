{{ config(location=lake_root() ~ '/mart/price_changes_yearly.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_price_changes') }}
order by farm_change - store_change
