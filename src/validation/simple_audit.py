import os
import glob
import pandas as pd
import logging
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
CLEAN_DIR = "data/clean"
AUDIT_LOG = "audit_log.txt"

# Thresholds (The Rules)
MIN_ROWS = 500       # Less than this = Empty Scrape?
MIN_REGIONS = 10     # Less than this = Partial Extraction (e.g. NCR only)

# Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

def get_latest_parquet():
    """Finds the most recent clean data file."""
    files = glob.glob(os.path.join(CLEAN_DIR, "market_prices_*.parquet"))
    if not files:
        return None
    # Sort by name (date is in name)
    return max(files, key=os.path.getmtime)

def run_audit():
    logger.info("👮 The Bouncer: Starting Audit...")
    
    latest_file = get_latest_parquet()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if not latest_file:
        logger.error("❌ CRITICAL: No data files found in Clean Layer.")
        log_result(f"FAIL: {today_str} | No Data Files Found")
        return False

    try:
        df = pd.read_parquet(latest_file)
        row_count = len(df)
        region_count = df['region_name'].nunique() if 'region_name' in df.columns else 0
        
        # Check 1: Volume
        if row_count < MIN_ROWS:
            msg = f"FAIL: {today_str} | Low Volume ({row_count} rows < {MIN_ROWS})"
            logger.error(f"❌ {msg}")
            log_result(msg)
            return False
            
        # Check 2: Reach
        if region_count < MIN_REGIONS:
            msg = f"FAIL: {today_str} | Low Coverage ({region_count} regions < {MIN_REGIONS})"
            logger.error(f"❌ {msg}")
            log_result(msg)
            return False
            
        # PASS
        msg = f"PASS: {today_str} | Rows: {row_count:,} | Regions: {region_count} | Source: {os.path.basename(latest_file)}"
        logger.info(f"✅ {msg}")
        log_result(msg)
        return True

    except Exception as e:
        logger.error(f"❌ Auditor Crashed: {e}")
        log_result(f"CRASH: {today_str} | {e}")
        return False

def log_result(message):
    """Appends result to a persistent text log."""
    with open(AUDIT_LOG, "a") as f:
        f.write(message + "\n")

if __name__ == "__main__":
    run_audit()
