import pdfplumber
import pandas as pd
import requests
import io
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime

# CONFIG
SRP_URL_BASE = "https://www.da.gov.ph/price-monitoring/"
OUTPUT_PATH = "data/reference/official_srp.csv"

# MAPPING DICTIONARY (PDF Name -> System Name)
# This maps the raw text from the PDF to our clean API names
NAME_MAPPING = {
    "V. Rice": "Rice",
    "Special": "Rice (Special)",
    "Premium": "Rice (Premium)",
    "Well Milled": "Rice (Well Milled)",
    "Regular Milled": "Rice (Regular Milled)",
    "Corn": "Corn",
    "Bangus": "Bangus",
    "Tilapia": "Tilapia",
    "Galunggal": "Galungong",
    "Galunggong": "Galungong",
    "Imported": "Galungong (Imported)",
    "Local": "Galungong (Local)",
    "Alumahan": "Alumahan",
    "Beef Rump": "Beef (Rump)",
    "Beef Brisket": "Beef (Brisket)",
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

def fetch_latest_pdf_url():
    print("🔎 Searching for latest Price Bulletin PDF...")
    try:
        response = requests.get(SRP_URL_BASE, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Target tablepress-129
        table = soup.find('table', id='tablepress-129')
        if not table:
             # Fallback
             print("⚠️ Table not found, searching links...")
             pdf_link = soup.find('a', href=re.compile(r'\.pdf$', re.IGNORECASE), text=re.compile(r'Price Bulletin', re.IGNORECASE))
             return pdf_link['href'] if pdf_link else None

        first_row = table.find('tbody').find('tr')
        if not first_row: return None
             
        link_tag = first_row.find('td', class_='column-1').find('a')
        if link_tag and 'href' in link_tag.attrs:
            url = link_tag['href']
            print(f"✅ Found latest PDF: {url}")
            return url
        return None
    except Exception as e:
        print(f"❌ Error scraping DA website: {e}")
        return None

def clean_price(price_str):
    try:
        # Handle ranges "45-50" -> take average? or max? or min? 
        # User wants "Prevailing", implies single number. 
        # If range, usually Prevailing is a separate col, but if parsing fails, we take mean.
        if '-' in str(price_str):
            parts = [float(re.sub(r'[^\d.]', '', p)) for p in str(price_str).split('-') if p.strip()]
            return sum(parts) / len(parts) if parts else None
        return float(re.sub(r'[^\d.]', '', str(price_str)))
    except:
        return None

def extract_benchmark_data(pdf_bytes):
    print("📄 Extracting 'Prevailing Retail Price' from PDF...")
    data = []
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            # We assume a structure where "Prevailing" is often the 3rd or 4th column
            # Strategy: Find "Commodity" header, then map relative columns
            
            tables = page.extract_tables()
            for table in tables:
                header_found = False
                prevailing_idx = -1
                
                # Header Analysis
                for i, row in enumerate(table[:5]):
                    row_clean = [str(c).lower().replace('\n', ' ') for c in row if c]
                    row_text = " ".join(row_clean)
                    
                    if "commodity" in row_text:
                        header_found = True
                        # Find "Prevailing" column index
                        for idx, col_val in enumerate(row_clean):
                            if "prevailing" in col_val or "price" in col_val:
                                prevailing_idx = idx
                                # Prefer "Prevailing" over just "Price" if both exist
                                if "prevailing" in col_val:
                                    break
                
                if header_found:
                    # Parse Data Rows
                    # Default if index not found: Try last column? Or 2nd to last?
                    # Let's use heuristic: Column with money pattern
                    
                    target_idx = prevailing_idx if prevailing_idx != -1 else -1 
                    
                    for row in table[i+1:]:
                        clean_row = [c for c in row if c and str(c).strip()]
                        if not clean_row: continue
                        
                        raw_name = clean_row[0].replace('\n', ' ').strip()
                        
                        # Find price
                        price = None
                        if target_idx != -1 and target_idx < len(row):
                             price = clean_price(row[target_idx])
                        
                        # Fallback: scan row for numbers
                        if price is None:
                            nums = []
                            for cell in clean_row[1:]:
                                p = clean_price(cell)
                                if p and p > 0: nums.append(p)
                            # Heuristic: Prevailing is usually the median or specifically marked.
                            # We take the first valid price found as a best effort
                            if nums: price = nums[0]
                        
                        # Unit Detection
                        unit = "kg"
                        if "pc" in str(row).lower(): unit = "pc"
                        
                        # Mapping
                        system_name = raw_name
                        # Fuzzy-ish match using dictionary
                        for key, val in NAME_MAPPING.items():
                            if key.lower() in raw_name.lower():
                                system_name = val
                                break
                        
                        if price:
                            data.append({
                                "commodity": system_name,
                                "official_srp": price,
                                "unit": unit,
                                "category": "General" # TODO: Map categories
                            })
                            
    return pd.DataFrame(data).drop_duplicates(subset=['commodity'])

def main():
    pdf_url = fetch_latest_pdf_url()
    if not pdf_url: return

    try:
        response = requests.get(pdf_url)
        df = extract_benchmark_data(response.content)
        
        if not df.empty:
            df.to_csv(OUTPUT_PATH, index=False)
            print(f"✅ Updated Benchmark Data: {len(df)} items.")
            print(df.head())
        else:
            print("⚠️ No data extracted.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
