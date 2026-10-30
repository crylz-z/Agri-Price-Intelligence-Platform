-- Clean prices: one row per (posting_date, region_id, market_name, commodity_name).
-- Inputs: `raw` (every raw row scraped in the last 14 days) and `run` (this run's rows).
-- Only posting dates this run touched are rebuilt; when a key was scraped more than
-- once, the latest extract_dt wins (price breaks exact ties, for a deterministic result).
SELECT
    posting_date,
    region_id,
    region_name,
    market_name,
    commodity_group,
    commodity_name,
    specifications,
    price,
    raw_date_text,
    extract_dt
FROM raw
WHERE posting_date IN (SELECT DISTINCT posting_date FROM run)
QUALIFY row_number() OVER (
    PARTITION BY posting_date, region_id, market_name, commodity_name
    ORDER BY extract_dt DESC, price DESC
) = 1
ORDER BY posting_date, region_id, market_name, commodity_name
