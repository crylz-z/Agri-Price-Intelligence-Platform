import requests
import time
from bs4 import BeautifulSoup

# CENTRAL LUZON
REGION_ID = "030000000" 
REGION_NAME = "REGION III (CENTRAL LUZON)"

# URLs
BASE_URL = "https://www.bantaypresyo.da.gov.ph/price-monitoring"
URL_DATE = f"{BASE_URL}/tbl_price_get_date.php"
URL_HEADER = f"{BASE_URL}/tbl_price_get_header.php"
URL_PRICE = f"{BASE_URL}/tbl_price_get_comm_price.php"

# Headers
HEADERS = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
    'X-Requested-With': 'XMLHttpRequest'
}

def debug_region():
    print(f"🕵️ SPY MODE ACTIVE: Investigating {REGION_NAME} ({REGION_ID})")
    print("="*60)
    
    # Test with just ONE category (e.g., RICE)
    CAT_ID = "1" 
    CAT_NAME = "RICE"
    
    payload_base = {'region': REGION_ID, 'commodity': CAT_ID}
    
    # 1. DATE CHECK
    print(f"\n[1] Checking DATE endpoint for {CAT_NAME}...")
    try:
        r = requests.post(URL_DATE, data=payload_base, headers=HEADERS, timeout=10)
        print(f"   Status: {r.status_code}")
        print(f"   Response Preview: {r.text[:100]}...")
        date_text = r.text.strip()
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return

    # 2. HEADER CHECK
    print(f"\n[2] Checking HEADER endpoint (Markets)...")
    try:
        r = requests.post(URL_HEADER, data=payload_base, headers=HEADERS, timeout=10)
        print(f"   Status: {r.status_code}")
        print(f"   Response Length: {len(r.text)}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        markets = [th.get_text(strip=True) for th in soup.find_all('th')]
        print(f"   Parsed Markets ({len(markets)}): {markets}")
        
        if not markets:
            print("   ⚠️ NO MARKETS FOUND. Server returned empty header table.")
            return
            
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return

    # 3. PRICE CHECK
    print(f"\n[3] Checking PRICE endpoint...")
    payload_price = payload_base.copy()
    payload_price['count'] = str(len(markets))
    
    try:
        r = requests.post(URL_PRICE, data=payload_price, headers=HEADERS, timeout=10)
        print(f"   Status: {r.status_code}")
        print(f"   Response Length: {len(r.text)}")
        print(f"   Response Content:\n{r.text[:500]}") # Print first 500 chars
        
        if "No record found" in r.text or "No data available" in r.text:
            print("\n🚨 CONCLUSION: GOVERNMENT DID NOT UPLOAD DATA (Empty Response).")
        elif not r.text.strip():
             print("\n🚨 CONCLUSION: SERVER TIMEOUT / BLOCKED (Empty String).")
        else:
             print("\n✅ CONCLUSION: DATA EXISTS. Pipeline might be failing to parse it.")
             
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

if __name__ == "__main__":
    debug_region()
