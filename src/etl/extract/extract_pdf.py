import os
import requests
import pdfplumber
import pandas as pd
from datetime import datetime
import logging

# ==========================================
# CONFIGURATION
# ==========================================
# Directory Config
RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"
TEMP_PDF_PATH = os.path.join(RAW_DIR, "temp_ncr_macro.pdf")

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL Pattern (Placeholder - needs adjustment to actual site structure)
# Example: https://www.da.gov.ph/wp-content/uploads/2023/10/Price-Monitoring-Report-NCR-2023-10-18.pdf
BASE_URL = "https://www.da.gov.ph/wp-content/uploads"

def fetch_latest_pdf():
    """
    Attempts to download the daily PDF report.
    Constructs URL based on today's date.
    """
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d") # e.g. 2023-10-18
    year = today.strftime("%Y")
    month = today.strftime("%m")
    
    # Construct potential URLs (Try a few common formats)
    # 1. Standard: .../2023/10/Price-Monitoring-Report-NCR-2023-10-18.pdf
    # 2. Variant: .../2023/10/Price-Watch-NCR-2023-10-18.pdf
    
    candidates = [
        f"{BASE_URL}/{year}/{month}/Price-Monitoring-Report-NCR-{date_str}.pdf",
        f"{BASE_URL}/{year}/{month}/Price-Watch-NCR-{date_str}.pdf"
    ]
    
    for url in candidates:
        try:
            logger.info(f"Attempting to fetch: {url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(TEMP_PDF_PATH, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Successfully downloaded to {TEMP_PDF_PATH}")
                return True
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            
    logger.error("Could not find/download today's PDF report.")
    return False

def extract_tables_from_pdf(pdf_path):
    """
    Uses pdfplumber to extract tables from all pages.
    """
    all_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                logger.info(f"Processing page {i+1}...")
                tables = page.extract_tables()
                
                for table in tables:
                    # Table is a list of lists
                    # Cleanse basic structure
                    df = pd.DataFrame(table)
                    all_data.append(df)
                    
        return all_data
    except Exception as e:
        logger.error(f"PDF Extraction failed: {e}")
        return []

def clean_and_normalize(raw_dfs):
    """
    Consolidates raw table fragments into a clean DataFrame.
    """
    if not raw_dfs:
        return pd.DataFrame()
    
    # Assumption: The first row of the first valid table contains headers
    # We iterate to find a table that looks like data
    
    consolidated = pd.DataFrame()
    
    for df in raw_dfs:
        # cleanup
        df = df.replace(r'\n', ' ', regex=True) # Remove newlines in cells
        
        # Check if this frame has the header we expect (e.g. Commodity)
        # Typically row 0 or 1
        
        # Simple heuristic: Look for 'Commodity' in first few rows
        header_idx = -1
        for idx, row in df.iterrows():
            row_str = " ".join([str(x) for x in row.values]).lower()
            if 'commodity' in row_str or 'prevailing' in row_str:
                header_idx = idx
                break
        
        if header_idx != -1:
            # Set header
            df.columns = df.iloc[header_idx]
            df = df.iloc[header_idx+1:]
            consolidated = pd.concat([consolidated, df], ignore_index=True)
            
    if consolidated.empty:
        return pd.DataFrame()
        
    # Standardize Headers
    # "Commodity" -> "commodity"
    # "Prevailing Price" -> "price"
    
    consolidated.columns = [str(c).strip().lower() for c in consolidated.columns]
    
    # Rename for consistency
    rename_map = {}
    for c in consolidated.columns:
        if 'commodity' in c:
            rename_map[c] = 'commodity'
        elif 'prevailing' in c or 'price' in c:
            rename_map[c] = 'prevailing_price'
            
    consolidated = consolidated.rename(columns=rename_map)
    
    # Keep only relevant columns
    if 'commodity' in consolidated.columns and 'prevailing_price' in consolidated.columns:
         final_df = consolidated[['commodity', 'prevailing_price']].copy()
    else:
        logger.warning("Could not identify core columns (commodity, price). Returning raw dump.")
        return consolidated
        
    # Clean Data
    final_df = final_df.dropna(subset=['commodity'])
    final_df = final_df[final_df['commodity'] != '']
    final_df['prevailing_price'] = pd.to_numeric(final_df['prevailing_price'], errors='coerce')
    
    # Add Extract Date
    final_df['extract_dt'] = datetime.now().strftime("%Y-%m-%d")
    final_df['source'] = 'DA Bantay Presyo PDF'
    
    return final_df

def run_extraction():
    logger.info("🚀 Starting PDF Extraction Pipeline...")
    
    # 1. Fetch
    if not fetch_latest_pdf():
        logger.warning("Skipping extraction due to download failure.")
        return
        
    # 2. Extract
    raw_tables = extract_tables_from_pdf(TEMP_PDF_PATH)
    
    # 3. Clean
    df_clean = clean_and_normalize(raw_tables)
    
    if df_clean.empty:
        logger.error("Extraction resulted in empty dataset.")
    else:
        # 4. Save
        today_str = datetime.now().strftime("%Y-%m-%d")
        output_file = os.path.join(CLEAN_DIR, f"ncr_macro_{today_str}.parquet")
        
        df_clean.to_parquet(output_file, index=False)
        logger.info(f"✅ Data saved to {output_file} ({len(df_clean)} rows)")
        
    # 5. Cleanup
    if os.path.exists(TEMP_PDF_PATH):
        os.remove(TEMP_PDF_PATH)
        logger.info("🗑️ Temp PDF removed.")

if __name__ == "__main__":
    run_extraction()
