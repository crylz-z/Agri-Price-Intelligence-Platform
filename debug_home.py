import requests
import re

url = 'http://www.bantaypresyo.da.gov.ph'
print(f"Fetching {url}...")
try:
    resp = requests.get(url, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"HTML Start: {resp.text[:500]}")
    
    # Generic link finder
    links = re.findall(r'(href|src)=["\'](.*?)["\']', resp.text)
    print(f"Found {len(links)} links.")
    
    for _, link in links:
        if 'price' in link or 'monitoring' in link or '.php' in link:
            print(f"MATCH: {link}")
            
except Exception as e:
    print(f"Error: {e}")
