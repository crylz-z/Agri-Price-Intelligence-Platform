import os
import glob
import pandas as pd
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = "data/clean"

def inspect_latest_parquet():
    """
    Phase 1: The 'X-Ray' Validation.
    Scans for the latest Parquet file and prints vital stats.
    """
    logger.info("🔍 STARTING PARQUET INSPECTION...\n")

    # 1. Find Files
    files = glob.glob(os.path.join(DATA_DIR, "*.parquet"))
    if not files:
        logger.error(f"❌ No Parquet files found in {DATA_DIR}")
        return

    # 2. Get Latest
    latest_file = max(files, key=os.path.getctime)
    logger.info(f"📂 Loading Latest File: {os.path.basename(latest_file)}")
    
    try:
        # 3. Load Data
        df = pd.read_parquet(latest_file)
        
        # 4. Print Stats
        total_rows = len(df)
        unique_regions = df['region_name'].nunique() if 'region_name' in df.columns else 0
        unique_commodities = df['commodity'].nunique() if 'commodity' in df.columns else 0
        
        logger.info(f"📊 Total Rows: {total_rows:,}")
        logger.info(f"🌍 Unique Regions: {unique_regions}")
        logger.info(f"🍎 Unique Commodities: {unique_commodities}")
        
        # 5. Region Breakdown
        if 'region_name' in df.columns:
            logger.info("\n🗺️  Region Breakdown:")
            region_counts = df['region_name'].value_counts()
            for region, count in region_counts.items():
                logger.info(f"   - {region}: {count:,} records")
        
        # 6. Sample Data
        logger.info("\n👀 Sample Data (5 Rows):")
        print(df.head(5).to_markdown(index=False))
        
        logger.info("\n✅ INSPECTION COMPLETE: File is valid and ready for Dashboard.")
        
    except Exception as e:
        logger.error(f"❌ FAILED to read Parquet file: {e}")

if __name__ == "__main__":
    inspect_latest_parquet()
