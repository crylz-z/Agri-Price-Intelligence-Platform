import os
import glob
import pandas as pd
import hashlib
import logging
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
from src.core.config import RAW_DIR, CLEAN_DIR
os.makedirs(CLEAN_DIR, exist_ok=True)

# Shared Maps (Duplicated from Extract for strict isolation as requested)
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

# Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# ==========================================
# CORE LOGIC
# ==========================================

def clean_column_name(col):
    """
    Standardize column names to snake_case.
    e.g. "Market Name" -> "market_name"
    """
    return col.strip().lower().replace(' ', '_').replace('-', '_')

def clean_string(val):
    """
    Standardize text: Title Case, Strip Whitespace.
    """
    if pd.isna(val):
        return None
    return str(val).strip().title()

def generate_record_id(row):
    """
    Generate a deterministic hash for Primary Key.
    MD5(extract_dt + region_id + market_name + commodity)
    """
    raw_str = f"{row['extract_dt']}{row['region_id']}{row['market_name']}{row['commodity']}"
    return hashlib.md5(raw_str.encode()).hexdigest()

def process_file(filepath):
    """
    Reads and cleans a single CSV file.
    """
    try:
        if os.path.getsize(filepath) == 0:
            logger.warning(f"Skipping empty file: {filepath}")
            return None

        df = pd.read_csv(filepath)
        
        # 1. Standardize Columns
        df.columns = [clean_column_name(c) for c in df.columns]
        
        # 2. Type Casting & Cleaning
        # Price -> Float
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            # Drop invalid prices (0 or Negative) - Edge Case handling
            df = df[df['price'] > 0]
        
        # Strings -> Title Case
        for col in ['market_name', 'category', 'commodity']:
            if col in df.columns:
                df[col] = df[col].apply(clean_string)
        
        # Date -> Datetime
        if 'extract_dt' in df.columns:
            df['extract_dt'] = pd.to_datetime(df['extract_dt'])
            
        # 3. Enrichment
        # Add Region Name from Map (if available)
        if 'region_id' in df.columns:
            # Cast to string and Ensure 9-digit format (padding leading zeros)
            # e.g. 80000000 -> 080000000
            df['region_id'] = df['region_id'].astype(str).str.zfill(9)
            df['region_name'] = df['region_id'].map(REGION_MAP).fillna("Unknown Region")
            
        # 4. Generate Primary Key
        # Ensure we have required columns
        required_cols = ['extract_dt', 'region_id', 'market_name', 'commodity']
        if all(c in df.columns for c in required_cols):
             df['record_id'] = df.apply(generate_record_id, axis=1)
             
        return df

    except Exception as e:
        logger.error(f"Failed to process {filepath}: {e}")
        return None

def cleanup_silver_layer():
    """
    Enforce Silver Layer Policy: PURGE any .csv files in data/clean/.
    """
    csv_files = glob.glob(os.path.join(CLEAN_DIR, "*.csv"))
    for f in csv_files:
        try:
            os.remove(f)
            logger.info(f"🧹 Purged legacy file: {f}")
        except Exception as e:
            logger.warning(f"Failed to delete {f}: {e}")

def run_transform():
    """
    Main execution function:
    1. Scan Raw CSVs (Bronze)
    2. Clean & Merge (Silver)
    3. Save to Parquet (Silver)
    4. Cleanup Legacy CSVs
    """
    logger.info("🔨 Starting Silver Layer Transformation...")
    
    # 1. Scan Files (Recursive)
    all_files = glob.glob(os.path.join(RAW_DIR, "**", "prices_*.csv"), recursive=True)
    if not all_files:
        logger.warning("No raw files found to transform.")
        return

    logger.info(f"   Found {len(all_files)} raw files.")
    
    # 2. Process & Merge
    frames = [] 
    for fp in all_files:
        df = process_file(fp)
        if df is not None:
            frames.append(df)
            
    if not frames:
        logger.warning("No valid data extracted from files.")
        return
        
    df_silver = pd.concat(frames, ignore_index=True)
    
    # 3. Final Deduplication (Defensive)
    if 'record_id' in df_silver.columns:
        before_dedup = len(df_silver)
        df_silver = df_silver.drop_duplicates(subset=['record_id'], keep='last')
        dupes = before_dedup - len(df_silver)
        if dupes > 0:
            logger.info(f"   Dropped {dupes} duplicate rows based on record_id.")

    # 4. Partition/Save by Date (The "Midnight" Bug handling)
    if 'extract_dt' in df_silver.columns:
        for extract_dt, group in df_silver.groupby(df_silver['extract_dt'].dt.date):
            date_str = extract_dt.strftime("%Y-%m-%d")
            filename = f"market_prices_{date_str}.parquet"
            output_path = os.path.join(CLEAN_DIR, filename)
            
            # Save with Snappy
            group.to_parquet(output_path, engine='pyarrow', compression='snappy', index=False)
            logger.info(f"✅ Saved {output_path} ({len(group)} records)")
    else:
        logger.error("Critical: 'extract_dt' column missing. Cannot save partitioned files.")
        
    # 5. Policy Enforcement
    cleanup_silver_layer()

if __name__ == "__main__":
    run_transform()
