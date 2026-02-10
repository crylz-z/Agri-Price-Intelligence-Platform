import pandas as pd
import glob
import os
import re
from src.utils.logger import get_logger

# Configure Logging
logger = get_logger('clean_data')

RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"

def get_latest_file():
    files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
    if not files:
        return None
    return max(files, key=os.path.getctime)

def clean_market_name(name):
    """Standardize 'Mkt.' to 'Market' and title case."""
    if pd.isna(name):
        return "Unknown Market"
    name = str(name).strip()
    name = re.sub(r'Mkt\.?', 'Market', name, flags=re.IGNORECASE)
    return name.title()

def validate_data(df, filename):
    """The Gatekeeper: Fail if data looks garbage."""
    # 1. Volume Check
    if len(df) < 10:
        raise ValueError(f"Data Volume Error: Only {len(df)} rows found in {filename}. Expected > 10.")
    
    # 2. Price Reality Check
    avg_price = df['price'].mean()
    if avg_price < 10 or avg_price > 2000:
        raise ValueError(f"Price Reality Error: Average price is ₱{avg_price:.2f}. This indicates bad units or parsing.")
    
    # 3. Null Check
    null_prices = df['price'].isnull().sum()
    if null_prices > len(df) * 0.5:
        raise ValueError(f"Data Quality Error: {null_prices}/{len(df)} rows have no price.")

    logger.info("✅ Data Validation Passed.")

def transform():
    # Ensure clean dir exists
    os.makedirs(CLEAN_DIR, exist_ok=True)
    
    # 1. Load Latest Raw
    latest_file = get_latest_file()
    if not latest_file:
        logger.warning("No raw files found.")
        return
    
    logger.info(f"Processing: {latest_file}")
    df = pd.read_csv(latest_file)
    
    # 2. Clean
    # Standardize Market Names
    df['market_name'] = df['market_name'].apply(clean_market_name)
    
    # Force Numeric Prices
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Drop Invalid Rows
    initial_len = len(df)
    df = df.dropna(subset=['price', 'market_name'])
    df = df[df['price'] > 0] # Remove zero/negative prices
    
    dropped = initial_len - len(df)
    if dropped > 0:
        logger.info(f"Dropped {dropped} invalid rows (NaN or <=0 price).")
    
    # Deduplicate
    df = df.drop_duplicates()
    
    # 3. Validate (The Gatekeeper)
    try:
        validate_data(df, latest_file)
    except ValueError as e:
        logger.error(f"🚨 VALIDATION FAILED: {e}")
        # We raise the error to crash the GitHub Action (Red X)
        raise e
        
    # 4. Save
    filename = os.path.basename(latest_file).replace('ncr_prices_', 'ncr_clean_')
    output_path = os.path.join(CLEAN_DIR, filename)
    df.to_csv(output_path, index=False)
    logger.info(f"✅ Success. Saved {len(df)} clean rows to {output_path}")

if __name__ == "__main__":
    transform()
