import requests
import csv
import os
import time
from bs4 import BeautifulSoup
from config.settings import PRICES_URL, HEADERS_URL, USER_AGENTS
from src.utils.logger import get_logger

logger = get_logger('fetch_metadata')

# Range of IDs to scan (Standard categories 1-15 approx)
SCAN_RANGE = range(1, 20) 
REGION_ID = '130000000' # Scrape NCR for catalog building

def fetch_metadata():
    logger.info("🕵️  Starting API Catalog Discovery (Scanning IDs 1-20)...")
    
    unique_items = set()
    
    for com_id in SCAN_RANGE:
        try:
            payload = {
                'region': REGION_ID,
                'commodity': str(com_id),
                'count': '10' # Fetch a few to check existence
            }
            
            headers = {
                'User-Agent': USER_AGENTS[0],
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            }
            
            # Rate limit
            time.sleep(1)
            
            resp = requests.post(PRICES_URL, data=payload, headers=headers, timeout=30)
            if "No Record Found" in resp.text:
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            rows = soup.find_all('tr')
            
            if not rows:
                continue
                
            logger.info(f"  > ID {com_id}: Found {len(rows)} rows.")
            
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if not cols: 
                    continue
                    
                # Extract basic info
                # Row structure varies, but usually Col 0 is Name, Col 1 is Spec (if offset)
                # We need to be smart.
                # However, brute force usually returns simple TRs inside the table body?
                # Actually, the API returns a TABLE BODY usually.
                
                raw_text = [c.text.strip() for c in cols]
                if not raw_text: continue
                
                name = raw_text[0]
                spec = ""
                
                # Heuristic: If col 1 is specification (text, not price)
                # Prices are usually numbers. Specs are text like 'KG', 'Piece'.
                # But sometimes col 1 is price?
                # Let's clean the name and save it. 
                # If name is "Corn (White)", that's good.
                
                if name and "No Record" not in name:
                    unique_items.add(name)
                    
        except Exception as e:
            logger.error(f"Error scanning ID {com_id}: {e}")

    # Save
    if unique_items:
        os.makedirs('data/reference', exist_ok=True)
        csv_path = 'data/reference/api_catalog.csv'
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['commodity_id', 'commodity_name']) # ID is placeholder
            writer.writeheader()
            for item in sorted(unique_items):
                writer.writerow({'commodity_id': '0', 'commodity_name': item})
                
        logger.info(f"✅ API Catalog saved to {csv_path} ({len(unique_items)} items).")
    else:
        logger.warning("❌ No items discovered.")

if __name__ == "__main__":
    fetch_metadata()
