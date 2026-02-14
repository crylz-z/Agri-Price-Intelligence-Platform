import os
import glob
import pandas as pd
import logging
from datetime import datetime
from src.core.config import REGION_MAP, CLEAN_DIR, METRICS_DIR, LOGS_DIR

# ==========================================
# CONFIGURATION
# ==========================================
AUDIT_LOG = os.path.join(LOGS_DIR, "audit_log.txt")

# Thresholds (The Rules)
MIN_ROWS = 500       
MIN_REGIONS = 5      # Relaxed for now, but monitored
PRICE_SWING_THRESHOLD = 1.0 # 100% variance

# Mandatory Regions (Must be present for a "PASS")
MANDATORY_REGIONS = [
    "NCR (NATIONAL CAPITAL REGION)",
    "REGION III (CENTRAL LUZON)",
    "REGION IV-A (CALABARZON)"
]

# Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

def get_latest_parquet_files(n=2):
    """Finds the n most recent clean data files."""
    files = glob.glob(os.path.join(CLEAN_DIR, "market_prices_*.parquet"))
    if not files:
        return []
    # Sort by name (date is in name) descending
    sorted_files = sorted(files, key=os.path.getmtime, reverse=True)
    return sorted_files[:n]

def log_result(message):
    """Appends result to a persistent text log."""
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    with open(AUDIT_LOG, "a", encoding='utf-8') as f:
        f.write(message + "\n")

def run_audit():
    logger.info("👮 The Bouncer: Starting Enhanced Audit...")
    
    files = get_latest_parquet_files(2)
    if not files:
        logger.error("❌ CRITICAL: No data files found in Clean Layer.")
        log_result(f"FAIL: {datetime.now()} | No Data Files Found")
        return False
        
    latest_file = files[0]
    prev_file = files[1] if len(files) > 1 else None
    today_str = datetime.now().strftime("%Y-%m-%d")

    try:
        df = pd.read_parquet(latest_file)
        row_count = len(df)
        
        # 1. Integrity Check
        if not pd.api.types.is_numeric_dtype(df['price']):
             logger.error("❌ CRITICAL: Price column is not numeric.")
             return False
        
        # 2. Volume Check
        if row_count < MIN_ROWS:
            msg = f"FAIL: {today_str} | Low Volume ({row_count} < {MIN_ROWS})"
            logger.error(f"❌ {msg}")
            log_result(msg)
            return False

        # 3. Mandatory Regions Check
        present_regions = df['region_name'].unique()
        missing_critical = [r for r in MANDATORY_REGIONS if r not in present_regions]
        if missing_critical:
            msg = f"WARNING: {today_str} | Missing Critical Regions: {missing_critical}"
            logger.warning(f"⚠️  {msg}")
            log_result(msg)
            # We don't fail the pipeline for this yet, just warn
            
        # 4. Anomaly Detection (Price Swings)
        if prev_file:
            logger.info(f"🔍 Comparing with {os.path.basename(prev_file)}...")
            df_prev = pd.read_parquet(prev_file)
            
            # Avg Price per Commodity
            curr_avg = df.groupby('commodity')['price'].mean()
            prev_avg = df_prev.groupby('commodity')['price'].mean()
            
            # Merge
            comparison = pd.concat([curr_avg, prev_avg], axis=1, keys=['curr', 'prev']).dropna()
            comparison['variance'] = abs((comparison['curr'] - comparison['prev']) / comparison['prev'])
            
            anomalies = comparison[comparison['variance'] > PRICE_SWING_THRESHOLD]
            
            if not anomalies.empty:
                logger.warning(f"⚠️  Found {len(anomalies)} commodities with >100% price swing.")
                for comm, row in anomalies.iterrows():
                    logger.warning(f"    - {comm}: ₱{row['prev']:.2f} -> ₱{row['curr']:.2f} ({row['variance']*100:.0f}%)")
                    log_result(f"ANOMALY: {today_str} | {comm} swung {row['variance']*100:.0f}%")
            else:
                logger.info("✅ No extreme price anomalies detected.")
                
        # PASS
        msg = f"PASS: {today_str} | Rows: {row_count:,} | Regions: {len(present_regions)} | Source: {os.path.basename(latest_file)}"
        logger.info(f"✅ {msg}")
        log_result(msg)
        return True

    except Exception as e:
        logger.error(f"❌ Auditor Crashed: {e}")
        log_result(f"CRASH: {today_str} | {e}")
        return False

if __name__ == "__main__":
    run_audit()
