
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
where 
    -- Sanity Check: Price (Agri prices > 20,000 are errors)
    price <= 20000
    and price >= 0
    -- Sanity Check: Region Name (Filter out "1000000", "400000.0" etc)
    and not regexp_matches(region_name, '^[0-9.]+$')
