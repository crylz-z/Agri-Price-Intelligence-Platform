
with source as (
    select * from {{ source('agri_prices_bronze', 'market_prices') }}
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
