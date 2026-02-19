import sys
import os
import time
import logging
import argparse
import concurrent.futures
from datetime import datetime
import pandas as pd

# Framework Imports
from src.core.config import REGION_MAP, CATEGORY_MAP, BASE_URL, DATA_DIR, RAW_DIR, METRICS_DIR
from src.core.http_client import AgriHttpClient
from src.core.io_manager import IOManager

# Logging Setup
from src.core.config import LOGS_DIR
os.makedirs(LOGS_DIR, exist_ok=True)
log_file = os.path.join(LOGS_DIR, "scraper.log")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize Core Components
http_client = AgriHttpClient()
io_manager = IOManager()

# Constants
URL_DATE = f"{BASE_URL}/tbl_price_get_date_rice.php"
URL_HEADER = f"{BASE_URL}/tbl_price_get_comm_header.php"
URL_PRICE = f"{BASE_URL}/tbl_price_get_comm_price.php"
METRICS_FILE = os.path.join(METRICS_DIR, "pipeline_health.csv")

def fetch_category_data(region_id, category_id, category_name, timeout):
    try:
        payload_base = {'region': region_id, 'commodity': category_id}

        # Step 1: Get Date
        response = http_client.post(URL_DATE, data=payload_base, timeout=timeout)
        date_text = response.text

        # Step 2: Get Headers
        response = http_client.post(URL_HEADER, data=payload_base, timeout=timeout)
        headers_html = response.text
        
        # Parse Headers
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(headers_html, 'html.parser')
        markets = [td.get_text(strip=True) for td in soup.find_all('td', class_='text-wrap')]
        markets = [m for m in markets if m and "SPECIFICATIONS" not in m.upper()]
        
        if not markets:
            return None

        # Step 3: Get Prices
        payload_price = payload_base.copy()
        payload_price['count'] = str(len(markets))
        
        response = http_client.post(URL_PRICE, data=payload_price, timeout=timeout)
        prices_html = response.text
        
        # Parse Prices
        parsed_data = parse_price_rows(prices_html, markets, region_id, category_name, date_text)
        return parsed_data

    except Exception as e:
        return None

def parse_price_rows(html_rows, market_list, region_id, category_name, payload_date):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_rows, 'html.parser')
    parsed_data = []
    rows = soup.find_all('tr')
    
    current_date_str = datetime.now().strftime("%Y-%m-%d")

    for row in rows:
        cells = row.find_all(['td', 'th'])
        if not cells: continue
        
        try:
            comm_name = cells[0].get_text(strip=True)
            specs = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            full_commodity_name = f"{comm_name} - {specs}" if specs else comm_name
            price_cells = cells[2:]

            for market, cell in zip(market_list, price_cells):
                price_str = cell.get_text(strip=True)
                if not price_str or price_str in ['N/A', '-', '']: continue
                
                try:
                    clean_price = float(price_str.replace(',', ''))
                except ValueError:
                    continue

                row_date = row.get('data-date') or row.get('data-price_date')
                final_date = current_date_str
                
                if row_date:
                    final_date = row_date
                elif payload_date:
                    try:
                        dt = datetime.strptime(payload_date, "%B %d, %Y")
                        final_date = dt.strftime("%Y-%m-%d")
                    except ValueError:
                        pass
                
                parsed_data.append({
                    'extract_dt': final_date,
                    'region_id': region_id,
                    'market_name': market,
                    'category': category_name,
                    'commodity': full_commodity_name,
                    'price': clean_price
                })
        except Exception:
            continue
            
    return parsed_data

def process_region(args):
    """
    Worker function to process a single region.
    """
    region_id, region_name, mode_config = args
    timeout = mode_config['timeout']
    breaker_limit = mode_config['breaker_limit']
    
    start_time = time.time()
    total_records = 0
    consecutive_failures = 0
    
    logger.info(f"🚀 START: {region_name} ({region_id})...")
    
    all_region_data = []
    
    try:
        for cat_id, cat_name in CATEGORY_MAP.items():
            # Circuit Breaker Check
            if breaker_limit and consecutive_failures >= breaker_limit:
                logger.warning(f"⚠️  CIRCUIT BREAKER: {region_name} - Skipping remaining categories.")
                break

            try:
                rows = fetch_category_data(region_id, cat_id, cat_name, timeout)
                
                if rows:
                    all_region_data.extend(rows)
                    consecutive_failures = 0 
                else:
                    consecutive_failures += 1
                
                time.sleep(0.5)
                
            except Exception as e:
                consecutive_failures += 1
                logger.warning(f"  > Error in {cat_name}: {e}")

        # Save Data
        if all_region_data:
            df = pd.DataFrame(all_region_data)
            for extract_dt, group in df.groupby('extract_dt'):
                timestamp = int(time.time())
                
                # Create Date Subdirectory
                date_dir = os.path.join(RAW_DIR, extract_dt)
                os.makedirs(date_dir, exist_ok=True)
                
                filename = f"prices_{region_name}_{extract_dt}.csv"
                filepath = os.path.join(date_dir, filename)
                
                existing_df = io_manager.load_dataframe(filepath, file_format='csv')
                if not existing_df.empty:
                    combined = pd.concat([existing_df, group], ignore_index=True)
                    deduped = combined.drop_duplicates(subset=['region_id', 'market_name', 'commodity', 'extract_dt'], keep='last')
                    io_manager.save_dataframe(deduped, filepath, file_format='csv', mode='overwrite')
                    total_records += len(group)
                else:
                    io_manager.save_dataframe(group, filepath, file_format='csv', mode='overwrite')
                    total_records += len(group)

        duration = time.time() - start_time
        status = "OK" if total_records > 0 else "NO_DATA"
        logger.info(f"✅ DONE: {region_name} | {total_records} rows | {duration:.2f}s")
        return (region_name, status, total_records, duration)

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ FAIL: {region_name} | Error: {e}")
        return (region_name, f"FAIL ({e})", 0, duration)

def main():
    parser = argparse.ArgumentParser(description="Agri-Price Extraction Engine")
    parser.add_argument('--mode', choices=['scout', 'harvester'], default='scout', help='Execution mode')
    args = parser.parse_args()
    
    # Adaptive Configuration
    if args.mode == 'scout':
        config = {'timeout': 10, 'breaker_limit': 3, 'workers': 5}
    else: # harvester
        config = {'timeout': 60, 'breaker_limit': None, 'workers': 8}
        
    logger.info(f"🚀 Starting Extraction Engine (Mode: {args.mode.upper()})")
    logger.info(f"   Timeout: {config['timeout']}s | Breaker: {config['breaker_limit']} | Workers: {config['workers']}")
    
    pipeline_start = time.time()
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=config['workers']) as executor:
        # Pass config to workers
        region_args = [(rid, rname, config) for rid, rname in REGION_MAP.items()]
        future_results = executor.map(process_region, region_args)
        
        for res in future_results:
            results.append(res)
            
    pipeline_end = time.time()
    total_duration = pipeline_end - pipeline_start
    total_rows = sum(r[2] for r in results)
    
    # Telemetry
    for rname, status, rows, dur in results:
        metric = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'mode': args.mode,
            'region': rname,
            'status': status,
            'rows_extracted': rows,
            'duration_seconds': round(dur, 2)
        }
        io_manager.append_metric_row(METRICS_FILE, metric)
        
    logger.info(f"🏁 Pipeline Finished. Metrics saved to {METRICS_FILE}")
    logger.info(f"TOTAL ROWS: {total_rows}")

    # Trigger Downstream
    try:
        from src.etl.transform.clean_data import run_transform
        from src.validation.simple_audit import run_audit
        run_transform()
        run_audit()
    except Exception as e:
        logger.error(f"Downstream Trigger Failed: {e}")

if __name__ == "__main__":
    main()
