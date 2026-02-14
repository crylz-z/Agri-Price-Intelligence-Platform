import os

# Base Configuration
BASE_URL = "http://www.bantaypresyo.da.gov.ph"
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.0

# Mappings
REGION_MAP = {
    '140000000': 'CAR (CORDILLERA ADMINISTRATIVE REGION)',
    '010000000': 'REGION I (ILOCOS REGION)',
    '020000000': 'REGION II (CAGAYAN VALLEY)',
    '030000000': 'REGION III (CENTRAL LUZON)',
    '040000000': 'REGION IV-A (CALABARZON)',
    '170000000': 'REGION IV-B (MIMAROPA)',
    '050000000': 'REGION V (BICOL REGION)',
    '060000000': 'REGION VI (WESTERN VISAYAS)',
    '070000000': 'REGION VII (CENTRAL VISAYAS)',
    '080000000': 'REGION VIII (EASTERN VISAYAS)',
    '090000000': 'REGION IX (ZAMBOANGA PENINSULA)',
    '100000000': 'REGION X (NORTHERN MINDANAO)',
    '110000000': 'REGION XI (DAVAO REGION)',
    '120000000': 'REGION XII (SOCCSKSARGEN)',
    '130000000': 'NCR (NATIONAL CAPITAL REGION)',
    '150000000': 'BARMM (Bangsamoro Autonomous Region of Muslim Mindanao)',
    '160000000': 'REGION XIII (Caraga)'
}

CATEGORY_MAP = {
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

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, os.getenv("AGRI_DATA_DIR", "data"))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
