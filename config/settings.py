USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
]

BASE_URL = "http://www.bantaypresyo.da.gov.ph"
HEADERS_URL = f"{BASE_URL}/tbl_price_get_comm_header.php"
PRICES_URL = f"{BASE_URL}/tbl_price_get_comm_price.php"

# Region Code for NCR
REGION_ID = '130000000'

# Commodity Map (Discovered via Script)
COMMODITIES = {
    '1': 'Rice',
    '2': 'Corn',
    '3': 'Legumes',
    '4': 'Fish',
    '5': 'Fruits',
    '6': 'Highland Vegetables',
    '7': 'Lowland Vegetables',
    '8': 'Meat and Poultry',
    '9': 'Spices',
    '10': 'Other Commodities'
}
