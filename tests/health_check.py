import os
import sys
import pandas as pd
import glob

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_project_structure():
    """Verify standard folders exist."""
    required_dirs = ['src', 'data/raw', 'logs', 'config']
    missing = [d for d in required_dirs if not os.path.isdir(d)]
    
    if missing:
        print(f"[FAIL] Missing directories: {missing}")
        return False
    print("[PASS] Project structure is valid.")
    return True

def test_config_validity():
    """Verify settings.py is importable and has commodities."""
    try:
        from config.settings import COMMODITIES, REGION_ID
        if not COMMODITIES:
            print("[FAIL] COMMODITIES dict is empty.")
            return False
        if REGION_ID != '130000000':
            print(f"[FAIL] REGION_ID is {REGION_ID}, expected '130000000' (NCR).")
            return False
        print(f"[PASS] Configuration loaded. Targeted Commodities: {len(COMMODITIES)}")
        return True
    except ImportError as e:
        print(f"[FAIL] Could not import settings: {e}")
        return False

def test_data_integrity():
    """Verify the latest CSV file has data and correct schema."""
    files = glob.glob('data/raw/*.csv')
    if not files:
        print("[FAIL] No CSV files found in data/raw/.")
        return False
    
    latest_file = max(files, key=os.path.getctime)
    try:
        df = pd.read_csv(latest_file)
        
        # 1. Check Columns
        expected_cols = ['extract_dt', 'region_id', 'market_name', 'category', 'commodity', 'price']
        if list(df.columns) != expected_cols:
            print(f"[FAIL] Schema mismatch. \nExpected: {expected_cols}\nFound: {list(df.columns)}")
            return False
            
        # 2. Check Data Volume
        if len(df) < 100:
            print(f"[FAIL] Data volume too low: {len(df)} rows. Expected >100.")
            return False
            
        # 3. Check Commodity Diversity (At least 3 categories)
        unique_cats = df['category'].nunique()
        if unique_cats < 3:
            print(f"[FAIL] Only found {unique_cats} commodity categories. Expected >3.")
            return False
            
        print(f"[PASS] Data integrity verified on {os.path.basename(latest_file)}.")
        print(f"       Rows: {len(df)} | Categories: {unique_cats}")
        return True
        
    except Exception as e:
        print(f"[FAIL] Error reading CSV: {e}")
        return False

if __name__ == "__main__":
    print("Running System Health Check...\n" + "="*30)
    s = test_project_structure()
    c = test_config_validity()
    d = test_data_integrity()
    print("="*30)
    
    if s and c and d:
        print("✅ SYSTEM READY FOR PRODUCTION")
    else:
        print("❌ SYSTEM CHECKS FAILED")
