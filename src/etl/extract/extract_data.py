import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import logging

# ==========================================
# CONFIGURATION (Strict & Hardcoded)
# ==========================================

# 1. Region Map (Source of Truth)
REGION_MAP = {
    '140000000': 'CAR (CORDILLERA ADMINISTRATIVE REGION)',
    '010000000': 'REGION I (ILOCOS REGION)',
    '020000000': 'REGION II (CAGAYAN VALLEY)',
    '030000000': 'REGION III (CENTRAL LUZON)',
    '040000000': 'REGION IV-A (CALABARZON)',
    '170000000': 'REGION IV-B (MIMAROPA)',
    '050000000': 'REGION V (BICOL REGION)',
    '060000000': 'REGION VI (WESTERN VISAYAS)',
    '070000000': 'REGION VII (CENTRAL VISAYAS)',
    '080000000': 'REGION VIII (EASTERN VISAYAS)',
    '090000000': 'REGION IX (ZAMBOANGA PENINSULA)',
    '100000000': 'REGION X (NORTHERN MINDANAO)',
    '110000000': 'REGION XI (DAVAO REGION)',
    '120000000': 'REGION XII (SOCCSKSARGEN)',
    '130000000': 'NCR (NATIONAL CAPITAL REGION)',
    '150000000': 'BARMM (Bangsamoro Autonomous Region of Muslim Mindanao)',
    '160000000': 'REGION XIII (Caraga)'
}

# 2. Category Map (Source of Truth)
CATEGORY_MAP = {
    '1': 'Rice',
    '2': 'Corn',
    '3': 'Legumes',
    '4': 'Fish',
    '5': 'Fruits',
    '6': 'Highland Vegetables',
    '7': 'Lowland Vegetables',
    '8': 'Meat and Poultry',
    '9': 'Spices',
    '10': 'Other Commodities'
}

# 3. API Endpoints
BASE_URL = "http://www.bantaypresyo.da.gov.ph"
# The API requires a 3-step sequence:
# Step 1: Get Date string
URL_DATE = f"{BASE_URL}/tbl_price_get_date_rice.php"
# Step 2: Get Table Headers (Markets)
URL_HEADER = f"{BASE_URL}/tbl_price_get_comm_header.php"
# Step 3: Get Prices (Data)
URL_PRICE = f"{BASE_URL}/tbl_price_get_comm_price.php"

# 4. Request Settings & Session Pooling (The VIP Line)
HEADERS = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
    'X-Requested-With': 'XMLHttpRequest'
}

# Session Factory
session = requests.Session()
session.headers.update(HEADERS)

# Mount Adapter for faster retries (Socket Level)
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=2,                # Maximum number of retries
    backoff_factor=1,       # Wait 1s, 2s, 4s...
    status_forcelist=[500, 502, 503, 504], # Retry on these errors
    allowed_methods=["POST"] # Retry on POST requests
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)


# 5. Output Conf
DATA_DIR = "data/raw"
os.makedirs(DATA_DIR, exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# ==========================================
# CORE LOGIC
# ==========================================

def fetch_with_retry(url, payload, description):
    """
    Pillar 3: Resilient Fetcher with Session Pooling & Aggressive Timeouts.
    """
    try:
        # Timeout=10s (The "Impatient Customer" Strategy)
        response = session.post(url, data=payload, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        # We don't need a loop retry here because HTTPAdapter handles it.
        # If we get here, it means we failed after retries or timed out.
        logger.warning(f"  > FAILED: {description}. Error: {e}")
        return None

def parse_header_markets(html_headers):
    """
    Parses Step 2 response (Headers) to extract Market List and Count.
    """
    soup = BeautifulSoup(html_headers, 'html.parser')
    # Markets are usually in <td class="text-wrap">COMMONWEALTH MARKET</td>
    # But sometimes they are TH? Or weirdly structured.
    # Browser inspection showed: <tr>...<td class="text-wrap">MARKET NAME</td>...</tr>
    markets = [td.get_text(strip=True) for td in soup.find_all('td', class_='text-wrap')]
    
    # Filter out empty or "SPECIFICATIONS" if present
    markets = [m for m in markets if m and "SPECIFICATIONS" not in m.upper()]
    return markets

def parse_price_rows(html_rows, market_list, region_id, category_name, payload_date):
    """
    Parses Step 3 response (Prices) and maps them to markets.
    """
    soup = BeautifulSoup(html_rows, 'html.parser')
    parsed_data = []
    
    # Each TR is a commodity row
    rows = soup.find_all('tr')
    
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if not cells:
            continue
            
        # Structure: [Name, Specs, Price1, Price2, ... PriceN]
        # Sometimes Name/Specs are combined? 
        # Usually: Call 1 = Name, Cell 2 = Specs.
        current_date_str = datetime.now().strftime("%Y-%m-%d")

        try:
            # COMMODITY NAME
            comm_name = cells[0].get_text(strip=True)
            
            # SPECIFICATIONS
            specs = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            full_commodity_name = f"{comm_name} - {specs}" if specs else comm_name

            # PRICES (Remaining cells)
            price_cells = cells[2:]
            
            # Safety check: Ensure price cells match market count
            # Use zip to safely pair them
            for market, cell in zip(market_list, price_cells):
                price_str = cell.get_text(strip=True)
                
                # Clean Price
                clean_price = None
                if price_str and price_str not in ['N/A', '-', '']:
                    try:
                        clean_price = float(price_str.replace(',', ''))
                    except ValueError:
                        continue # Skip invalid numbers

                if clean_price is not None:
                    # Content-Based Routing (Pillar 4)
                    # Try to find data-date attribute on the row or cell
                    # If not found, fall back to payload_date (Step 1 result)
                    # NOTE: Browser inspection showed date is separate. 
                    # We will use payload_date as the primary specific date.
                    row_date = row.get('data-date') or row.get('data-price_date')
                    
                    # Convert 'February 11, 2026' to '2026-02-11' if using payload_date
                    final_date = current_date_str # Default fallback
                    
                    if row_date:
                        final_date = row_date # Assume it's YYYY-MM-DD? Need to verify format.
                    elif payload_date:
                        try:
                            # Parse "February 11, 2026"
                            dt = datetime.strptime(payload_date, "%B %d, %Y")
                            final_date = dt.strftime("%Y-%m-%d")
                        except ValueError:
                            # Log warning but keep going?
                            # logger.warning(f"Could not parse date: {payload_date}")
                            pass

                    parsed_data.append({
                        'extract_dt': final_date,
                        'region_id': region_id,
                        'market_name': market,
                        'category': category_name,
                        'commodity': full_commodity_name,
                        'price': clean_price
                    })

        except Exception as e:
            # logger.warning(f"Error parsing row: {e}")
            continue
            
    return parsed_data

def idempotent_upsert(new_data):
    """
    Pillar 5: Read-Merge-Dedup-Write.
    Groups data by 'extract_dt' (Content-Based Routing) and upserts to correct file.
    """
    if not new_data:
        return

    df = pd.DataFrame(new_data)
    
    # Group by Date (Routing)
    for extract_dt, group in df.groupby('extract_dt'):
        # Target File
        # We need region name for filename. 
        # Since new_data can be mixed regions (if we ran multiple), we group by region too?
        # The Orchestrator runs per region. So all rows here *should* be one region?
        # No, strictness: Group by Region ID too.
        
        for region_id, region_group in group.groupby('region_id'):
            region_name = REGION_MAP.get(region_id, "UNKNOWN_REGION")
            filename = f"prices_{region_name}_{extract_dt}.csv"
            target_path = os.path.join(DATA_DIR, filename)
            
            try:
                # 1. Read Existing
                if os.path.exists(target_path):
                    df_existing = pd.read_csv(target_path)
                    df_combined = pd.concat([df_existing, region_group], ignore_index=True)
                else:
                    df_combined = region_group
                
                # 2. Dedup (Keep Last)
                # Fingerprint: Region + Market + Commodity + Date
                # Category included implicitly by commodity uniqueness? Ideally yes.
                subset = ['region_id', 'market_name', 'commodity', 'extract_dt']
                df_dedup = df_combined.drop_duplicates(subset=subset, keep='last')
                
                # 3. Write Atomic
                temp_path = target_path + ".tmp"
                df_dedup.to_csv(temp_path, index=False)
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.rename(temp_path, target_path)
                
                logger.info(f"    -> Upserted {len(region_group)} rows to {filename} (Total: {len(df_dedup)})")
                
            except Exception as e:
                logger.error(f"    -> Failed to write {filename}: {e}")


import concurrent.futures

# ... (Imports remain the same) ...

# ==========================================
# CORE LOGIC
# ==========================================

# ... (fetch_with_retry, parse_header_markets, parse_price_rows, idempotent_upsert remain the same) ...

def process_region_wrapper(args):
    """
    Wrapper for Parallel execution.
    Args: (region_id, region_name)
    Returns: (region_name, status, row_count, duration_seconds)
    """
    region_id, region_name = args
    start_time = time.time()
    region_records = 0
    
    logger.info(f"🚀 START: {region_name} ({region_id})...")
    
    try:
        region_buffer = []
        
        for cat_id, cat_name in CATEGORY_MAP.items():
            # Step 1: Get Date
            payload_base = {'region': region_id, 'commodity': cat_id}
            date_text = fetch_with_retry(URL_DATE, payload_base, f"Date for {cat_name}")
            
            # Step 2: Get Headers
            headers_html = fetch_with_retry(URL_HEADER, payload_base, f"Headers for {cat_name}")
            if not headers_html: continue
            
            markets = parse_header_markets(headers_html)
            if not markets: continue
                
            # Step 3: Get Prices
            payload_price = payload_base.copy()
            payload_price['count'] = str(len(markets))
            
            prices_html = fetch_with_retry(URL_PRICE, payload_price, f"Prices for {cat_name}")
            if not prices_html: continue
            
            # Parse & Collect
            rows = parse_price_rows(prices_html, markets, region_id, cat_name, date_text)
            if rows:
                region_buffer.extend(rows)
            
            # Helper Sleep (per category, inside thread)
            time.sleep(0.5)

        # Flush to Disk
        if region_buffer:
            idempotent_upsert(region_buffer)
            region_records = len(region_buffer)
            
        duration = time.time() - start_time
        logger.info(f"✅ DONE: {region_name} | {region_records} rows | {duration:.2f}s")
        return (region_name, "OK", region_records, duration)

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ FAIL: {region_name} | Error: {e}")
        return (region_name, f"FAIL ({e})", 0, duration)


def main():
    logger.info("🚀 Starting Extraction Engine V2.1 (The Conveyor Belt)...")
    logger.info(f"   Target: {len(REGION_MAP)} Regions | Parallel Workers: 5")
    
    pipeline_start = time.time()
    results = []
    
    # PARALLEL EXECUTION (Pillar 6)
    # We use max_workers=5 to balance speed and load.
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Prepare arguments as tuples
        region_args = [(rid, rname) for rid, rname in REGION_MAP.items()]
        
        # Launch map
        # executor.map returns results in order
        future_results = executor.map(process_region_wrapper, region_args)
        
        for res in future_results:
            results.append(res)
            
    pipeline_end = time.time()
    total_duration = pipeline_end - pipeline_start
    total_rows = sum(r[2] for r in results)
    
    # PERFORMANCE REPORT
    logger.info("\n" + "="*50)
    logger.info(f"📊 PERFORMANCE REPORT (Total: {total_duration:.2f}s)")
    logger.info("="*50)
    logger.info(f"{'REGION':<30} | {'STATUS':<10} | {'ROWS':<5} | {'DURATION'}")
    logger.info("-" * 65)
    
    for rname, status, rows, dur in results:
        dur_str = f"{dur:.2f}s"
        logger.info(f"{rname:<30} | {status:<10} | {rows:<5} | {dur_str}")
        
    logger.info("-" * 65)
    logger.info(f"TOTAL ROWS EXTRACTED: {total_rows}")
    logger.info("="*50)

    # TRIGGER SILVER LAYER (The Chain Reaction)
    try:
        from src.etl.transform.clean_data import run_transform
        from src.validation.simple_audit import run_audit
        
        # 1. Transform
        run_transform()
        
        # 2. Audit (The Bouncer)
        run_audit()
        
    except ImportError as e:
        logger.error(f"Pipeline Import Error: {e}")
    except Exception as e:
        logger.error(f"Pipeline Failed: {e}")

if __name__ == "__main__":
    main()
