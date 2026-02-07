import requests
import pandas as pd
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import os
import time
import random

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "http://www.bantaypresyo.da.gov.ph"
HEADERS_URL = f"{BASE_URL}/tbl_price_get_comm_header.php"
PRICES_URL = f"{BASE_URL}/tbl_price_get_comm_price.php"

# Configuration (Payloads)
# Region 130000000 = NCR
# Commodity 8 = Meat
# Count 31 = Default/Max items per page? (needs verification, but using PRD value)
PAYLOAD = {
    'region': '130000000',
    'commodity': '8',
    'count': '31'
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]

def get_headers():
    """Fetch the market names (table headers)."""
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        response = requests.post(HEADERS_URL, data=PAYLOAD, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching headers: {e}")
        return None

def get_prices():
    """Fetch the price data (table body)."""
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        response = requests.post(PRICES_URL, data=PAYLOAD, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching prices: {e}")
        return None

def parse_data(html_headers, html_prices):
    """Parse HTML and combine headers and prices into a DataFrame."""
    if not html_headers or not html_prices:
        return None

    try:
        # Parse Headers
        soup_headers = BeautifulSoup(html_headers, 'html.parser')
        markets = [th.text.strip() for th in soup_headers.find_all('th')]
        
        # The first header is usually 'Commodity' or empty, let's check
        # Based on typical tables, the first column is the row label (Commodity)
        # and the rest are Markets.
        # Let's clean up the market names.
        markets = [m for m in markets if m] # Remove empty strings if any
        
        # Parse Prices
        soup_prices = BeautifulSoup(html_prices, 'html.parser')
        rows = soup_prices.find_all('tr')
        
        data = []
        
        for row in rows:
            cols = row.find_all('td')
            if not cols:
                continue
            
            # First column is the Commodity Name
            commodity = cols[0].text.strip()
            
            # Remaining columns are Prices corresponding to Markets
            # We need to make sure the number of price columns matches the number of markets
            # The API might be tricky. Let's handle it dynamically.
            
            # Store raw prices first
            prices = [col.text.strip() for col in cols[1:]]
            
            # Map correctly?
            # Assumption: len(prices) == len(markets)
            # If not, we log a warning and try to align or skip.
            
            if len(prices) != len(markets):
                 logger.warning(f"Mismatch for {commodity}: {len(markets)} markets vs {len(prices)} prices. Truncating/Filling.")
                 # Simple strategy: slice to min length
                 min_len = min(len(prices), len(markets))
                 prices = prices[:min_len]
                 # Reconstruct truncated markets list for this row? No, simpler to just zip what we have.
            
            for market, price_str in zip(markets, prices):
                data.append({
                    'extract_dt': datetime.now().date(),
                    'region_id': PAYLOAD['region'],
                    'market_name': market,
                    'commodity': commodity,
                    'price_raw': price_str
                })
                
        return pd.DataFrame(data)

    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return None

def clean_data(df):
    """Clean and type-cast the DataFrame."""
    if df is None or df.empty:
        return df

    # 1. Handle 'N/A', empty strings, etc.
    df['price'] = df['price_raw'].replace({'N/A': None, '': None, '-': None})
    
    # 2. Remove commas and convert to float
    # Regex to keep only digits and decimal point
    df['price'] = df['price'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # 3. Add Availability Flag
    df['availability'] = df['price'].notnull() & (df['price'] > 0)
    
    # 4. Filter logic (optional: remove rows with no price? Or keep them as logs?)
    # PRD says identifying "Supply Chain Gaps (stock-outs)", so N/A is valuable data!
    # We keep them.
    
    return df

def save_data(df, format='parquet'):
    """Save data to data/ directory."""
    if df is None or df.empty:
        logger.warning("No data to save.")
        return

    today = datetime.now().strftime('%Y-%m-%d')
    file_name = f"data/ncr_meat_{today}"
    
    if format == 'parquet':
        output_path = f"{file_name}.parquet"
        try:
            df.to_parquet(output_path, index=False)
            logger.info(f"Saved {len(df)} records to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save Parquet: {e}")
            # Fallback
            output_path = f"{file_name}.csv"
            df.to_csv(output_path, index=False)
            logger.info(f"Fallback: Saved to {output_path}")
    else:
        output_path = f"{file_name}.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(df)} records to {output_path}")

def main():
    logger.info("Starting scraper...")
    
    # 1. Fetch
    html_headers = get_headers()
    html_prices = get_prices()
    
    if not html_headers or not html_prices:
        logger.error("Failed to fetch data. Exiting.")
        return

    # 2. Parse
    df = parse_data(html_headers, html_prices)
    
    # 3. Clean
    df_clean = clean_data(df)
    
    # 4. Save
    save_data(df_clean, format='parquet')
    
    logger.info("Scraping completed.")

if __name__ == "__main__":
    main()
