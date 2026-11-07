{{ config(location=lake_root() ~ '/mart/staple_seasonality.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_staple_seasonality') }}
order by staple, calendar_month
