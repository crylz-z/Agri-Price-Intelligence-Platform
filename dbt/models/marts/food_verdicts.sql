{{ config(location=lake_root() ~ '/mart/food_verdicts.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_food_verdicts') }}
order by middle_change desc
