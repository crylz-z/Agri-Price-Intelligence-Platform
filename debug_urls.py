import requests

BASE_URL = "http://www.bantaypresyo.da.gov.ph"
PATHS = [
    "/price-monitoring/tbl_price_get_comm_header.php",
    "/price-monitoring/price_get_comm_header.php",
    "/price-monitoring/get_comm_header.php",
    "/price-monitoring/e_get_comm_header.php",
    "/price-monitoring/comm_header.php",
    "/price-monitoring/header.php",
    
    "/price_monitoring/tbl_price_get_comm_header.php",
    "/monitoring/tbl_price_get_comm_header.php",
    "/tbl_price_get_comm_header.php",
    
    # Try Price variants too
    "/price-monitoring/tbl_price_get_comm_price.php",
    "/price-monitoring/get_comm_price.php",
    "/price-monitoring/price.php"
]

print(f"Testing {len(PATHS)} URLs on {BASE_URL}...")

for path in PATHS:
    url = BASE_URL + path
    try:
        # Send a dummy POST to see if we get 200 or 500 (which means file exists)
        # 404 means file not found.
        # Minimal payload
        resp = requests.post(url, data={'region': '130000000'}, timeout=5)
        print(f"[{resp.status_code}] {url}")
        if resp.status_code in [200, 500, 403]:
            print(f"!!! FOUND !!! {url}")
    except Exception as e:
        print(f"[ERR] {url} - {e}")
