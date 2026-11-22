{{ config(location=lake_root() ~ '/mart/seasonal_baseline.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_seasonal_baseline') }}
order by staple, calendar_month
