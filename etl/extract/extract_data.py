import sys
import os
import time
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
import random

from config.settings import HEADERS_URL, PRICES_URL, REGION_ID, COMMODITIES, USER_AGENTS
from src.utils.logger import get_logger

# Setup Directory Structure
os.makedirs('data/raw', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Setup Logging
logger = get_logger('extract_data')

def get_response(url, payload):
    """Helper to fetch data with polite headers."""
    headers = {
        'User-Agent': USER_AGENTS[0],
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")
        return None

def parse_table(html_headers, html_prices, commodity_name, payload):
    """
    Robust parsing logic handling 'td' vs 'th' tags in headers
    and identifying 'Specifications' offsets.
    """
    if not html_headers or not html_prices:
        return None

    try:
        soup_headers = BeautifulSoup(html_headers, 'html.parser')
        
        # 1. robust header extraction (handle th vs td)
        header_row = soup_headers.find('tr')
        if not header_row:
             # Fallback
             raw_headers = [th.text.strip() for th in soup_headers.find_all('th')]
        else:
             raw_headers = [cell.text.strip() for cell in header_row.find_all(['th', 'td'])]
        
        raw_headers = [m for m in raw_headers if m] # Remove empty strings

        # 2. Determine Offset (Commodity vs Commodity+Specs)
        header_offset = 0
        if raw_headers and raw_headers[0].upper() == 'COMMODITY':
            header_offset += 1
            if len(raw_headers) > 1 and raw_headers[1].upper() == 'SPECIFICATIONS':
                header_offset += 1
        
        markets = raw_headers[header_offset:]
        
        # 3. Parse Prices
        soup_prices = BeautifulSoup(html_prices, 'html.parser')
        rows = soup_prices.find_all('tr')
        
        row_data = []
        
        for row in rows:
            cols = row.find_all('td')
            if not cols or len(cols) < header_offset:
                continue
            
            # Extract Commodity Name & Spec
            item_name = cols[0].text.strip()
            if header_offset == 2:
                spec = cols[1].text.strip()
                if spec:
                    item_name = f"{item_name} - {spec}"
            
            # Extract Prices
            prices = [col.text.strip() for col in cols[header_offset:]]
            
            # Align
            # Truncate prices if more than markets (common issue)
            if len(prices) > len(markets):
                prices = prices[:len(markets)]
            
            for market, price_str in zip(markets, prices):
                # Basic cleaning
                clean_price = None
                if price_str and price_str not in ['N/A', '-', '']:
                    # Remove commas, keep digits/dots
                    try:
                        clean_price = float(price_str.replace(',', ''))
                    except ValueError:
                        clean_price = None

                row_data.append({
                    'extract_dt': datetime.now().date(),
                    'region_id': payload['region'],
                    'market_name': market,
                    'category': commodity_name,
                    'commodity': item_name,
                    'price': clean_price
                })
                
        return row_data

    except Exception as e:
        logger.error(f"Error parsing {commodity_name}: {e}")
        return []

def main():
    logger.info("Initializing Master Extraction Loop (NCR)...")
    
    all_records = []
    
    for com_id, com_name in COMMODITIES.items():
        logger.info(f"Fetching {com_name} (ID: {com_id})...")
        
        payload = {
            'region': REGION_ID,
            'commodity': com_id,
            'count': '31' # Fetch max
        }
        
        # 1. Rate Check
        time.sleep(2) 
        
        # 2. Fetch
        html_h = get_response(HEADERS_URL, payload)
        html_p = get_response(PRICES_URL, payload)
        
        # 3. Parse
        records = parse_table(html_h, html_p, com_name, payload)
        
        if records:
            all_records.extend(records)
            logger.info(f"  > Scanned {len(rows)} items. Extracted {len(records)} valid price records.")
        else:
            logger.warning(f"  > Scanned {len(rows)} items. No valid prices found for {com_name}.")

    # 4. Save
    if all_records:
        df = pd.DataFrame(all_records)
        filename = f"data/raw/ncr_prices_{datetime.now().strftime('%Y-%m-%d')}.csv"
        df.to_csv(filename, index=False)
        logger.info("="*50)
        logger.info(f"COMPLETED. Saved {len(df)} total records to {filename}")
        logger.info("="*50)
    else:
        logger.error("Extraction Failed: No data collected.")

if __name__ == "__main__":
    main()
