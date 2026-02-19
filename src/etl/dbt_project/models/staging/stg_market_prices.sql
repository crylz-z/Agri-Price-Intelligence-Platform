-- Staging model: reads Bronze Parquet files directly from S3 via DuckDB httpfs.
-- This bypasses the dbt-duckdb external source plugin requirement and works with
-- the :memory: DuckDB profile as long as the httpfs + aws extensions are loaded
-- (configured in profiles.yml).
--
-- Source path mirrors the dlt filesystem destination:
--   s3://<bucket>/bronze/dlt/market_data/agri_price_resource/*.parquet

with source as (
    select * from read_parquet(
        's3://{{ env_var("S3_BUCKET_NAME") }}/bronze/dlt/market_data/**/*.parquet'
    )
),

renamed as (
    select
        try_cast(extract_dt as timestamp) as extract_ts,
        region_id,
        region_name,
        market_name,
        commodity_group,
        commodity_name,
        specifications,
        try_cast(price as double) as price,
        raw_date_text,
        _dlt_load_id
    from source
)

select * from renamed
where
    -- Sanity check: agri prices above ₱20,000 are data errors.
    price <= 20000
    and price >= 0
    -- Sanity check: filter rows where region_name is a raw numeric ID (e.g. "1000000", "40000000.0").
    and not regexp_matches(region_name, '^[0-9.]+$')
