{{ config(location=lake_root() ~ '/mart/change_only_monthly.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_change_only_prices') }}
order by staple, month
