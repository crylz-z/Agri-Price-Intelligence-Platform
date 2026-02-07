import requests
import pandas as pd
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import os
import time
import random
import sys

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
# Commodity 2 = Corn (per User Request)
PAYLOAD = {
    'region': '130000000',
    'commodity': '2', 
    'count': '31'
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
]

def get_headers():
    """Fetch the market names (table headers)."""
    # headers = {'User-Agent': random.choice(USER_AGENTS)}
    headers = {'User-Agent': USER_AGENTS[0]} # Lock to known working agent
    try:
        response = requests.post(HEADERS_URL, data=PAYLOAD, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching headers: {e}")
        return None

def get_prices():
    """Fetch the price data (table body)."""
    # headers = {'User-Agent': random.choice(USER_AGENTS)}
    headers = {'User-Agent': USER_AGENTS[0]}
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
        # Find the header row (tr) first, then extract all cells (th and td)
        header_row = soup_headers.find('tr')
        if not header_row:
             # Fallback if just a list of th?
             raw_headers = [th.text.strip() for th in soup_headers.find_all('th')]
        else:
             raw_headers = [cell.text.strip() for cell in header_row.find_all(['th', 'td'])]
        
        raw_headers = [m for m in raw_headers if m] # Remove empty strings
        
        # Determine Header Offset
        header_offset = 0
        if raw_headers and raw_headers[0].upper() == 'COMMODITY':
            header_offset += 1
            if len(raw_headers) > 1 and raw_headers[1].upper() == 'SPECIFICATIONS':
                header_offset += 1
        
        markets = raw_headers[header_offset:]
        logger.info(f"Header Offset: {header_offset}")
        logger.info(f"Markets Found: {len(markets)}")
        
        if len(markets) == 0:
            logger.error(f"RAW HEADERS (First 500 chars): {html_headers[:500]}")
            logger.error(f"Parsed Raw Headers: {raw_headers}")


        
        # Parse Prices
        soup_prices = BeautifulSoup(html_prices, 'html.parser')
        rows = soup_prices.find_all('tr')
        
        data = []
        
        for row in rows:
            cols = row.find_all('td')
            if not cols:
                continue
            
            # Col 0 is always Commodity
            commodity_name = cols[0].text.strip()
            
            # Add Specifications to Commodity Name if exists
            full_commodity_name = commodity_name
            
            # Slice prices based on Offset
            # If offset is 2 (Comm + Spec), prices start at index 2
            # If offset is 1 (Comm), prices start at index 1
            
            # Safety check
            if len(cols) < header_offset:
                continue
                
            if header_offset == 2:
                spec = cols[1].text.strip()
                if spec:
                    full_commodity_name = f"{commodity_name} - {spec}"
            
            prices = [col.text.strip() for col in cols[header_offset:]]
            
            # Handle Mismatch
            if len(prices) != len(markets):
                 # logger.warning(f"Mismatch for {full_commodity_name}: {len(markets)} markets vs {len(prices)} prices. Truncating.")
                 min_len = min(len(prices), len(markets))
                 prices = prices[:min_len]
            
            for market, price_str in zip(markets, prices):
                data.append({
                    'extract_dt': datetime.now().date(),
                    'region_id': PAYLOAD['region'],
                    'market_name': market,
                    'commodity': full_commodity_name,
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
    
    # 2. Convert to float
    df['price'] = df['price'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # 3. Filter for valid prices only for calculation
    valid_data = df.dropna(subset=['price'])
    valid_data = valid_data[valid_data['price'] > 0]
    
    return valid_data

def run_corn_validation(df):
    """
    Performs the Corn Validation Test:
    1. Filter for Corn (Yellow) - Cob, Sweet Corn (Target Commodity)
    2. Calculate Stats.
    3. Compare with User Input.
    """
    if df is None or df.empty:
        logger.error("No data available for validation.")
        return

    # Filter for the specific corn type if possible, or just analyze all "Corn" items
    # Based on observation: "Corn (Yellow)" is the main category.
    # Let's look at unique commodities:
    commodities = df['commodity'].unique()
    target_commodity = None
    
    # Simple heuristic to find "Corn"
    for c in commodities:
        if "Corn" in c or "Sweet" in c:
            target_commodity = c
            break
    
    if not target_commodity:
        logger.warning(f"Could not find 'Corn' in commodities: {commodities}. Using first available.")
        target_commodity = commodities[0]

    logger.info(f"--- VALIDATION TARGET: {target_commodity} ---")
    
    subset = df[df['commodity'] == target_commodity]
    
    if subset.empty:
        logger.error("No valid price data for target commodity.")
        return

    # 1. Statistics
    avg_price = subset['price'].mean()
    min_price = subset['price'].min()
    max_price = subset['price'].max()
    cheapest_market = subset.loc[subset['price'].idxmin()]['market_name']
    expensive_market = subset.loc[subset['price'].idxmax()]['market_name']

    print("\n" + "="*50)
    print(f"🌽  CORN VALIDATION REPORT ({datetime.now().date()})")
    print("="*50)
    print(f"Target Commodity  : {target_commodity}")
    print(f"Data Points Found : {len(subset)}")
    print(f"Cheapest Market   : {cheapest_market} @ P{min_price:.2f}")
    print(f"Expensive Market  : {expensive_market} @ P{max_price:.2f}")
    print(f"API Calculated Avg: P{avg_price:.2f}")
    print("-" * 50)

    # 2. Interactive Validation
    print(">> PLEASE CHECK THE OFFICIAL DA PDF REPORT <<")
    try:
        pdf_input = input("Enter the PDF 'Prevailing Price' or Average (e.g., 83.13): ")
        pdf_average = float(pdf_input)
    except ValueError:
        logger.error("Invalid input. Using default benchmark of 83.13 for simulation.")
        pdf_average = 83.13

    # 3. Comparison
    diff = abs(avg_price - pdf_average)
    percent_diff = (diff / pdf_average) * 100
    
    print("-" * 50)
    print(f"Official PDF Avg  : P{pdf_average:.2f}")
    print(f"Variance (Diff)   : P{diff:.2f} ({percent_diff:.1f}%)")
    
    threshold = 15.0
    if percent_diff <= threshold:
        print("\n✅ VALIDATION PASSED! Data is within acceptable range.")
    else:
        print("\n⚠️  VALIDATION FAILED! Variance is too high.")
        print("Insight: The 'Commonwealth Market' anomaly (P50.00) might be dragging the average down.")
        print("Recommendation: Consider using Median or Weighted Average for future pipelines.")
    
    print("="*50 + "\n")

def main():
    logger.info("Starting scraper (Target: Corn)...")
    
    # 1. Fetch
    html_headers = get_headers()
    html_prices = get_prices()
    
    # 2. Parse
    df = parse_data(html_headers, html_prices)
    
    # 3. Clean and isolate valid numeric data
    df_clean = clean_data(df)
    
    # 4. Run Logic
    run_corn_validation(df_clean)
    
    # 5. Save (Optional for this step but good practice)
    # df_clean.to_csv("data/corn_validation.csv", index=False)

if __name__ == "__main__":
    main()
