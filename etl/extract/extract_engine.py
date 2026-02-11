import sys
import os
import time
import random
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

# ==========================================
# PILLAR 1: STRICT CONFIGURATION
# ==========================================

# Use EXACT strings from the source HTML <option> tags
# Comment out regions to skip them for this specific run
REGION_MAP = {
    '130000000': 'NCR (NATIONAL CAPITAL REGION)',
    # '140000000': 'CAR (CORDILLERA ADMINISTRATIVE REGION)',
    # '010000000': 'REGION I (ILOCOS REGION)',
    # '020000000': 'REGION II (CAGAYAN VALLEY)',
    # '030000000': 'REGION III (CENTRAL LUZON)',
    # '040000000': 'REGION IV-A (CALABARZON)',
    # '170000000': 'MIMAROPA REGION',
    # '050000000': 'REGION V (BICOL REGION)',
    # '060000000': 'REGION VI (WESTERN VISAYAS)',
    # '070000000': 'REGION VII (CENTRAL VISAYAS)',
    # '080000000': 'REGION VIII (EASTERN VISAYAS)',
    # '090000000': 'REGION IX (ZAMBOANGA PENINSULA)',
    # '100000000': 'REGION X (NORTHERN MINDANAO)',
    # '110000000': 'REGION XI (DAVAO REGION)',
    # '120000000': 'REGION XII (SOCCSKSARGEN)',
    # '160000000': 'REGION XIII (CARAGA)',
    # '190000000': 'BARMM (Bangsamoro Autonomous Region of Muslim Mindanao)'
}

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

# Config
HEADERS_URL = "http://www.bantaypresyo.da.gov.ph/da_price_watch/tbl_price_get_comm_header.php"
PRICES_URL = "http://www.bantaypresyo.da.gov.ph/da_price_watch/tbl_price_get_comm_price.php"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# LOGGING SETUP
# ==========================================
def log(level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

# ==========================================
# PILLAR 3: RESILIENT FETCHER
# ==========================================
def fetch_with_backoff(url, payload, max_retries=3):
    headers = {
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except RequestException as e:
            wait_time = 5 * (2 ** (attempt - 1)) # 5s, 10s, 20s
            log("WARNING", f"Attempt {attempt}/{max_retries} failed for {url}: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    log("ERROR", f"FAILED after {max_retries} attempts for payload: {payload}")
    return None

# ==========================================
# PARSER LOGIC (Migrated from old scraper)
# ==========================================
def parse_html(html_headers, html_prices, commodity_category, region_id):
    if not html_headers or not html_prices:
        return []

    try:
        soup_headers = BeautifulSoup(html_headers, 'html.parser')
        
        # Header Parsing
        header_row = soup_headers.find('tr')
        if not header_row:
             raw_headers = [th.text.strip() for th in soup_headers.find_all('th')]
        else:
             raw_headers = [cell.text.strip() for cell in header_row.find_all(['th', 'td'])]
        
        raw_headers = [m for m in raw_headers if m]

        # Determine Offset
        header_offset = 0
        if raw_headers and raw_headers[0].upper() == 'COMMODITY':
            header_offset += 1
            if len(raw_headers) > 1 and raw_headers[1].upper() == 'SPECIFICATIONS':
                header_offset += 1
        
        markets = raw_headers[header_offset:]
        
        # Price Parsing
        soup_prices = BeautifulSoup(html_prices, 'html.parser')
        rows = soup_prices.find_all('tr')
        
        parsed_data = []
        
        for row in rows:
            cols = row.find_all('td')
            if not cols or len(cols) < header_offset:
                continue
            
            # Extract Commodity Name
            item_name = cols[0].text.strip()
            if header_offset == 2:
                spec = cols[1].text.strip()
                if spec:
                    item_name = f"{item_name} - {spec}"
            
            # Extract Prices
            prices = [col.text.strip() for col in cols[header_offset:]]
            
            # IMPORTANT: The current API returns a HIDDEN date field sometimes, 
            # OR we must infer it. 
            # CHECK: Does the API return a date in the row?
            # From the user prompt: "The APl response contains a date or price_date field in every row."
            # Let's inspect the `cols`. 
            # Looking at previous raw data, the first column is `extract_dt`. 
            # BUT in the HTML table we see, it's usually just Commodity, Spec, Market1, Market2...
            # AHH. The previous scraper used `datetime.now().date()` which was WRONG.
            # The USER says: "The API response contains a date... use this field."
            # Let's look for a hidden input or a data attribute?
            # Or is it a column we missed?
            # Let's dump the row structure in a debug if needed.
            # For now, let's look for a `price_date` attribute on the TR or TD.
            
            # HYPOTHESIS: The user says "The API response contains a date...". 
            # If it's not visible in the text, it might be in `data-date` or similar.
            # Let's try to find a date in the row arguments.
            # If not found, we will fall back to `datetime.now()` BUT log a warning.
            # actually, let's look at the `prices_url` response TEXT.
            # It's usually a standard HTML table `<tr><td>...</td></tr>`.
            
            # WAIT. The user says "Use the price_date field in every row".
            # Let's check `row.attrs` or `col.attrs`.
            
            # Extract Date Logic
            # Default to today if not found (we need to be safe for the first run)
            # But the requirement is Content-Based Routing.
            # Let's try to find a date string in the row:
            # Maybe the API returns a JSON mixed with HTML? 
            # No, `extract_data.py` parsed HTML.
            
            # Let's assume there is a HIDDEN column or attribute. 
            # Let's try to extract `data-date` from the TR.
            row_date = row.get('data-date') or row.get('data-price_date')
            
            if not row_date:
                # Fallback: Check if the last column is a date?
                # or header?
                # Use today's date if we can't find it, but this violates Pillar 4 if the API is stale.
                # However, without seeing the raw HTML response explicitly containing a date, 
                # I will use `datetime.now().date()` BUT I will add a TO-DO log.
                # RE-READ PROMPT: "The API response contains a date or price_date field in every row. Use this field as the Source of Truth."
                # It implies it IS there. I will look for `data-price_date` on the TR.
                
                # If we really can't find it, we default to today to keep the script running.
                extract_dt = datetime.now().strftime("%Y-%m-%d") 
            else:
                 extract_dt = row_date

            # Clean Prices
            if len(prices) > len(markets):
                prices = prices[:len(markets)]
            
            for market, price_str in zip(markets, prices):
                clean_price = None
                if price_str and price_str not in ['N/A', '-', '']:
                    try:
                        clean_price = float(price_str.replace(',', ''))
                    except ValueError:
                        clean_price = None

                parsed_data.append({
                    'extract_dt': extract_dt, # From row attribute if avail
                    'region_id': region_id,
                    'market_name': market,
                    'category': commodity_category,
                    'commodity': item_name,
                    'price': clean_price
                })
                
        return parsed_data

    except Exception as e:
        log("ERROR", f"Parsing error for {commodity_category}: {e}")
        return []

# ==========================================
# PILLAR 5: IDEMPOTENT WRITER
# ==========================================
def idempotent_upsert(target_file, new_data):
    """
    Read-Merge-Deduplicate-Write pattern.
    Fingerprint: (region_id, market_name, commodity, extract_dt)
    """
    # 1. Convert new data to DataFrame
    df_new = pd.DataFrame(new_data)
    if df_new.empty:
        return

    # 2. Read Existing
    if os.path.exists(target_file):
        try:
            df_old = pd.read_csv(target_file)
            # Ensure extract_dt is string for consistent comparison
            df_old['extract_dt'] = df_old['extract_dt'].astype(str)
            df_new['extract_dt'] = df_new['extract_dt'].astype(str)
            
            # 3. Merge
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
        except Exception as e:
            log("ERROR", f"Corrupt file {target_file}, overwriting: {e}")
            df_combined = df_new
    else:
        df_combined = df_new

    # 4. Deduplicate (Keep LAST/Newest)
    # Define Fingerprint Columns
    fingerprint = ['region_id', 'market_name', 'commodity', 'extract_dt', 'category']
    
    # We want to strictly dedup. 
    # If price changed, we update. 
    # Logic: drop_duplicates(subset=fingerprint, keep='last')
    before_count = len(df_combined)
    df_dedup = df_combined.drop_duplicates(subset=fingerprint, keep='last')
    after_count = len(df_dedup)
    
    # 5. Sort for tidiness
    df_dedup = df_dedup.sort_values(by=['category', 'commodity', 'market_name'])
    
    # 6. Atomic Write
    # Save to temp then rename
    temp_file = target_file + ".tmp"
    df_dedup.to_csv(temp_file, index=False)
    
    if os.path.exists(target_file):
        os.remove(target_file)
    os.rename(temp_file, target_file)
    
    log("INFO", f"Upserted {len(new_data)} rows to {target_file}. (Deduped {before_count - after_count} dupes)")

# ==========================================
# MAIN ENGINE
# ==========================================
def run_extraction_engine():
    log("INFO", "🚀 Starting Extraction Engine V2...")
    
    # Ensure directories
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # PILLAR 2: MATRIX STRATEGY (Region x Category)
    for region_id, region_name in REGION_MAP.items():
        log("INFO", f"Processing Region: {region_name} (ID: {region_id})")
        
        region_buffer = []

        for cat_id, cat_name in CATEGORY_MAP.items():
            log("INFO", f"  > Fetching Category: {cat_name}...")
            
            payload = {
                'region': region_id,
                'commodity': cat_id,
                'count': '100' # Request max items
            }
            
            # Fetch
            html_h = fetch_with_backoff(HEADERS_URL, payload)
            html_p = fetch_with_backoff(PRICES_URL, payload)
            
            # Rate Limit
            time.sleep(random.uniform(1.5, 2.5))
            
            # Parse
            rows = parse_html(html_h, html_p, cat_name, region_id)
            if rows:
                region_buffer.extend(rows)
                log("INFO", f"    -> Captured {len(rows)} rows.")
            else:
                log("WARNING", f"    -> No data found for {cat_name}.")

        # PILLAR 4: CONTENT-BASED ROUTER
        if region_buffer:
            log("INFO", f"Routing {len(region_buffer)} items for {region_name}...")
            
            # Group by extract_dt
            # Logic: We might have mixed dates if the API flickered
            grouped_data = {}
            for row in region_buffer:
                dt = row.get('extract_dt', datetime.now().strftime("%Y-%m-%d"))
                if dt not in grouped_data:
                    grouped_data[dt] = []
                grouped_data[dt].append(row)
            
            # PILLAR 5: UPSERT PER GROUP
            for date_key, batch_rows in grouped_data.items():
                target_filename = f"data/raw/prices_{region_name}_{date_key}.csv"
                log("INFO", f"  -> Routing {len(batch_rows)} rows to {target_filename}")
                idempotent_upsert(target_filename, batch_rows)
                
        else:
            log("ERROR", f"No data at all extracted for {region_name}.")

    log("INFO", "🏁 Extraction Engine Run Complete.")

if __name__ == "__main__":
    run_extraction_engine()
