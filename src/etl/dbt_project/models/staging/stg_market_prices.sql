-- Staging model: reads Bronze Parquet files directly from S3 via DuckDB httpfs.
-- This bypasses the dbt-duckdb external source plugin requirement and works with
-- the :memory: DuckDB profile as long as the httpfs + aws extensions are loaded
-- (configured in profiles.yml).
--
-- Source path mirrors the dlt filesystem destination:
--   s3://<bucket>/bronze/dlt/market_data/agri_price_resource/*.parquet

with source as (
    select * from read_parquet(
        's3://{{ env_var("S3_BUCKET_NAME") }}/bronze/dlt/market_data/agri_price_resource/**/*.parquet',
        union_by_name=true
    )
),

renamed as (
    select
        try_cast(extract_dt as timestamp) as extract_ts,
        region_id,
        CASE
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '130000000' THEN 'NCR (NATIONAL CAPITAL REGION)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '140000000' THEN 'CAR (CORDILLERA ADMINISTRATIVE REGION)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '010000000' THEN 'REGION I (ILOCOS REGION)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '020000000' THEN 'REGION II (CAGAYAN VALLEY)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '030000000' THEN 'REGION III (CENTRAL LUZON)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '040000000' THEN 'REGION IV-A (CALABARZON)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '170000000' THEN 'REGION IV-B (MIMAROPA)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '050000000' THEN 'REGION V (BICOL REGION)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '060000000' THEN 'REGION VI (WESTERN VISAYAS)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '070000000' THEN 'REGION VII (CENTRAL VISAYAS)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '080000000' THEN 'REGION VIII (EASTERN VISAYAS)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '090000000' THEN 'REGION IX (ZAMBOANGA PENINSULA)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '100000000' THEN 'REGION X (NORTHERN MINDANAO)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '110000000' THEN 'REGION XI (DAVAO REGION)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '120000000' THEN 'REGION XII (SOCCSKSARGEN)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '150000000' THEN 'BARMM (Bangsamoro Autonomous Region of Muslim Mindanao)'
            WHEN LPAD(CAST(region_name AS VARCHAR), 9, '0') = '160000000' THEN 'REGION XIII (Caraga)'
            ELSE region_name
        END as region_name,
        market_name,
        commodity_group,
        commodity_name,
        try_cast(price as double) as price,
        raw_date_text,
        _dlt_load_id
    from source
)

select * from renamed
where
    price <= 20000
    and price >= 0
