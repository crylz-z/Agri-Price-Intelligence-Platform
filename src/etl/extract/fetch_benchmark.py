import requests
import pdfplumber
import pandas as pd
import io
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime

# CONFIG
URL_MONITORING = "https://www.da.gov.ph/price-monitoring/"
OUTPUT_FILE = "data/reference/official_srp.csv"
os.makedirs("data/reference", exist_ok=True)

# COMMODITY MAPPING
# PDF Name -> API/Clean Name
# We fuzzy match keys to raw text, map to values.
MAPPING = {
    "Rice Special": "Rice (Special)",
    "Rice Premium": "Rice (Premium)",
    "Rice Well Milled": "Rice (Well Milled)",
    "Rice Regular Milled": "Rice (Regular Milled)",
    "Corn": "Corn",
    "Bangus": "Bangus",
    "Tilapia": "Tilapia",
    "Galunggong": "Galungong",
    "Alumahan": "Alumahan",
    "Pork Kasim": "Pork (Kasim)",
    "Pork Liempo": "Pork (Liempo)",
    "Whole Chicken": "Chicken (Whole)",
    "Egg": "Egg (Medium)",
    "Red Onion": "Onion (Red)",
    "White Onion": "Onion (White)",
    "Imported Garlic": "Garlic (Imported)",
    "Native Garlic": "Garlic (Native)",
    "Ginger": "Ginger",
    "Tomato": "Tomato",
    "Cabbage": "Cabbage",
    "Carrot": "Carrot",
    "Habitchuelas": "Habitchuelas",
    "White Potato": "Potato (White)",
    "Pechay": "Pechay (Native)",
    "Sayote": "Sayote",
    "Ampalaya": "Ampalaya",
    "String Beans": "String Beans",
    "Eggplant": "Eggplant",
    "Squash": "Squash",
}

def get_latest_pdf_url():
    """Scrapes DA website for the latest Price Bulletin PDF link."""
    print("🌐 Connecting to DA Price Monitoring Page...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(URL_MONITORING, headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Heuristic: Find first link containing "Price Bulletin" or ending in .pdf
        # The DA site often puts the latest at the top of a table or list.
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            text = link.text.lower()
            if '.pdf' in href and ('Bulletin' in text or 'price' in text or 'monitor' in text):
                print(f"✅ Found PDF: {href}")
                return href
                
        # Fallback: specific table ID if known
        # tab = soup.find('table', id='tablepress-129') ...
        
        return None
    except Exception as e:
        print(f"❌ Error finding PDF: {e}")
        return None

def extract_from_pdf(pdf_bytes):
    """Extracts commodity prices from PDF bytes using pdfplumber."""
    print("📄 Parsing PDF...")
    data = []
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                # Need to identify columns.
                # Usually: Commodity | Unit | Prevailing Price
                # We look for header row.
                
                header_idx = -1
                price_col_idx = -1
                
                for i, row in enumerate(table):
                    row_str = " ".join([str(c).lower() for c in row if c])
                    if "commodity" in row_str:
                        header_idx = i
                        # Find price column
                        for j, col in enumerate(row):
                            if col and ("prevailing" in col.lower() or "price" in col.lower()):
                                price_col_idx = j
                                break
                        break
                
                if header_idx != -1 and price_col_idx != -1:
                    # Process data rows
                    for row in table[header_idx+1:]:
                        if not row or not row[0]: continue
                        
                        raw_name = str(row[0]).strip().replace('\n', ' ')
                        raw_price = str(row[price_col_idx]).strip()
                        
                        # Fuzzy Map Name
                        clean_name = None
                        for k, v in MAPPING.items():
                            if k.lower() in raw_name.lower():
                                clean_name = v
                                break
                        
                        # Parse Price
                        price_val = None
                        try:
                            # Handle ranges "200-220" -> Average
                            p_clean = re.sub(r'[^\d.-]', '', raw_price)
                            if '-' in p_clean:
                                parts = [float(x) for x in p_clean.split('-') if x]
                                if parts: price_val = sum(parts)/len(parts)
                            else:
                                price_val = float(p_clean)
                        except:
                            pass
                            
                        if clean_name and price_val:
                            data.append({
                                'commodity': clean_name,
                                'official_srp': price_val,
                                'unit': 'kg', # Default
                                'category': 'General' # Can refine later
                            })
                            
    return pd.DataFrame(data).drop_duplicates(subset=['commodity'])

def main():
    url = get_latest_pdf_url()
    if not url:
        print("⚠️ No PDF found. Aborting.")
        return

    try:
        print(f"⬇️ Downloading {url}...")
        resp = requests.get(url, timeout=30)
        df = extract_from_pdf(resp.content)
        
        if not df.empty:
            df.to_csv(OUTPUT_FILE, index=False)
            print(f"✅ Saved {len(df)} benchmarks to {OUTPUT_FILE}")
            print(df.head())
        else:
            print("⚠️ No valid data extracted from PDF.")
            
    except Exception as e:
        print(f"❌ Failed to process PDF: {e}")

if __name__ == "__main__":
    main()
