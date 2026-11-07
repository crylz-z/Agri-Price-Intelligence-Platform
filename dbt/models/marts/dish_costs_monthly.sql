{{ config(location=lake_root() ~ '/mart/dish_costs_monthly.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_dish_costs') }}
order by month, geo_code, dish
