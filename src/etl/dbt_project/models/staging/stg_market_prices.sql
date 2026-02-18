
with source as (
    select * from read_parquet('s3://{{ env_var('S3_BUCKET_NAME') }}/bronze/dlt/market_data/agri_price_resource/**/*.parquet')
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
