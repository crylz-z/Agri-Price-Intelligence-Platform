{{ config(location=lake_root() ~ '/mart/farmer_share_monthly.parquet') }}

-- Published to R2 only after every test upstream has passed.
select * from {{ ref('int_farmer_share') }}
order by month, geo_code, staple
