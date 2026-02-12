import pandas as pd
import os
import glob

# Configuration
CLEAN_DIR = "data/clean"

def load_parquet(date_str):
    """Load parquet file for a specific date."""
    filename = f"market_prices_{date_str}.parquet"
    filepath = os.path.join(CLEAN_DIR, filename)
    
    if os.path.exists(filepath):
        df = pd.read_parquet(filepath)
        print(f"✅ Loaded {filename}: {len(df)} rows")
        return df
    else:
        print(f"❌ File not found: {filename}")
        return None

def main():
    print("🔎 STARTING FORENSIC DATA COMPARISON 🔎")
    print("="*60)
    
    # 1. Load Data
    df_11 = load_parquet("2026-02-11")
    df_12 = load_parquet("2026-02-12")
    
    if df_11 is None or df_12 is None:
        print("⚠️ Missing data files. Cannot compare.")
        return

    # 2. Regional Comparison
    print("\n📊 REGIONAL BREAKDOWN")
    print("-" * 60)
    print(f"{'REGION':<40} | {'FEB 11':<8} | {'FEB 12':<8} | {'DIFF':<5}")
    print("-" * 60)
    
    # Group by Region Name
    count_11 = df_11.groupby('region_name').size().rename('Feb 11')
    count_12 = df_12.groupby('region_name').size().rename('Feb 12')
    
    # Merge
    comparison = pd.concat([count_11, count_12], axis=1).fillna(0).astype(int)
    comparison['Diff'] = comparison['Feb 12'] - comparison['Feb 11']
    
    # Sort by Diff (Ascending to see biggest drops)
    comparison = comparison.sort_values('Diff')
    
    for region, row in comparison.iterrows():
        print(f"{region:<40} | {row['Feb 11']:<8} | {row['Feb 12']:<8} | {row['Diff']:<5}")

    print("-" * 60)
    print(f"{'TOTAL':<40} | {len(df_11):<8} | {len(df_12):<8} | {len(df_12) - len(df_11):<5}")
    print("="*60)
    
    # 3. NCR Drill-Down
    print("\n🕵️ NCR DEEP DIVE")
    
    market_col = 'market' if 'market' in df_11.columns else 'market_name'
    if market_col not in df_11.columns:
         # Fallback to 3rd column if strictly positional
         if len(df_11.columns) > 2:
            market_col = df_11.columns[2]
         else:
            print("⚠️ Cannot identify market column.")
            return

    ncr_11 = df_11[df_11['region_name'].str.contains("NATIONAL CAPITAL", na=False)]
    ncr_12 = df_12[df_12['region_name'].str.contains("NATIONAL CAPITAL", na=False)]
    
    # Ensure market column exists in both
    if market_col not in ncr_12.columns:
        print(f"⚠️ Column '{market_col}' missing in Feb 12 data.")
        return

    mkts_11 = set(ncr_11[market_col].unique())
    mkts_12 = set(ncr_12[market_col].unique())
    
    missing_markets = mkts_11 - mkts_12
    new_markets = mkts_12 - mkts_11
    
    if missing_markets:
        print(f"❌ MISSING MARKETS IN FEB 12 ({len(missing_markets)}):")
        for m in sorted(missing_markets):
            print(f"   - {m}")
    else:
        print("✅ No missing markets in NCR.")
        
    if new_markets:
        print(f"✨ NEW MARKETS IN FEB 12 ({len(new_markets)}):")
        for m in sorted(new_markets):
             print(f"   + {m}")

if __name__ == "__main__":
    main()
