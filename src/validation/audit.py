import pandas as pd
import glob
import os
import sys

# Add project root to path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Config
CLEAN_DIR = "data/clean"
CATALOG_FILE = "data/reference/api_catalog.csv"

def normalize_name(name):
    return str(name).strip()

def audit_completeness():
    print("🧠 Starting API-First Pipeline Audit...")
    
    # 1. Load Reference Catalog (The Source of Truth)
    if not os.path.exists(CATALOG_FILE):
        print(f"❌ Catalog file missing: {CATALOG_FILE}")
        print("   Please run 'python src/fetch_metadata.py' first.")
        return

    catalog_df = pd.read_csv(CATALOG_FILE)
    reference_items = set(catalog_df['commodity_name'].apply(normalize_name))
    print(f"   Loaded {len(reference_items)} items from API Catalog.")

    # 2. Load Scraped Data
    files = glob.glob(os.path.join(CLEAN_DIR, "*.csv"))
    if not files:
        print("❌ No clean data found in data/clean/.")
        return
        
    latest_file = max(files, key=os.path.getctime)
    print(f"   Comparing against Scrape: {os.path.basename(latest_file)}")
    scrape_df = pd.read_csv(latest_file)
    
    scraped_items = set(scrape_df['commodity'].apply(normalize_name))
    
    # 3. Compare (Exact Match)
    # The API Catalog lists everything available on the website.
    # The Scrape should ideally capture all of it.
    
    missing_items = sorted(list(reference_items - scraped_items))
    extra_items = sorted(list(scraped_items - reference_items))
    
    matched_count = len(reference_items) - len(missing_items)
    
    # 4. Report
    report_lines = []
    report_lines.append("-" * 50)
    report_lines.append(f"INTELLIGENCE REPORT (API-First)")
    report_lines.append(f"Catalog Size: {len(reference_items)}")
    report_lines.append(f"Scraped Items: {len(scraped_items)}")
    report_lines.append(f"Matched: {matched_count}")
    report_lines.append(f"Coverage: {(matched_count/len(reference_items))*100:.1f}%")
    
    if missing_items:
        report_lines.append(f"\n⚠️  MISSING ITEMS (In Catalog, Not in Scrape): {len(missing_items)}")
        report_lines.append("    (This might mean they are out of stock today, or scraping failed for these items)")
        for m in missing_items:
            report_lines.append(f"   - {m}")
            
    if extra_items:
        report_lines.append(f"\n❓ NEW/EXTRA ITEMS (In Scrape, Not in Catalog): {len(extra_items)}")
        report_lines.append("    (The API Catalog might be outdated. Run 'src/fetch_metadata.py' to update.)")
        for e in extra_items:
            report_lines.append(f"   + {e}")

    # Print to Console
    for line in report_lines:
        print(line)
        
    # Save to File
    os.makedirs('reports', exist_ok=True)
    with open('reports/audit_latest.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    print(f"\n✅ Report saved to reports/audit_latest.txt")

if __name__ == "__main__":
    audit_completeness()
