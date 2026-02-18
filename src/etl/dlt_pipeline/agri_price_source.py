
import dlt
import time
import requests
from datetime import datetime
from typing import Iterator, Dict, Any, List, Optional
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import from existing project structure
from src.core.config import REGION_MAP, CATEGORY_MAP, BASE_URL
from src.core.http_client import AgriHttpClient
from src.utils.logger import get_logger

# Setup Logger
logger = get_logger(__name__)

# Constants
URL_DATE = f"{BASE_URL}/tbl_price_get_date_rice.php"
URL_HEADER = f"{BASE_URL}/tbl_price_get_comm_header.php"
URL_PRICE = f"{BASE_URL}/tbl_price_get_comm_price.php"

@dlt.source
def agri_price_source(limit: Optional[int] = None):
    """
    A dlt source for Agri-Price Intelligence Platform.
    """
    return agri_price_resource(limit=limit)

@dlt.resource(write_disposition="append")
def agri_price_resource(limit: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    """
    Yields price data dictionaries by scraping the government website.
    """
    http_client = AgriHttpClient()
    
    count = 0
    # Iterate over all regions and categories
    for region_id, region_name in REGION_MAP.items():
        for category_id, category_name in CATEGORY_MAP.items():
            if limit and count >= limit:
                return

            logger.info(f"Extracting: {region_name} - {category_name}")
            
            try:
                data = fetch_category_data(http_client, region_id, category_id, category_name)
                if data:
                    yield from data
                    count += 1
            except Exception as e:
                logger.error(f"Failed to fetch {region_name} - {category_name}", error=str(e))
                continue

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (requests.exceptions.RequestException, requests.exceptions.HTTPError)
    ),
)
def fetch_category_data(http_client, region_id, category_id, category_name) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches and parses data for a single category/region.
    """
    payload_base = {"region": region_id, "commodity": category_id}

    # Step 1: Get Date
    response = http_client.post(URL_DATE, data=payload_base)
    date_text = response.text

    # Step 2: Get Headers
    response = http_client.post(URL_HEADER, data=payload_base)
    headers_html = response.text

    # Parse Headers to get Markets
    soup = BeautifulSoup(headers_html, "html.parser")
    markets = [
        td.get_text(strip=True) for td in soup.find_all("td", class_="text-wrap")
    ]
    markets = [m for m in markets if m and "SPECIFICATIONS" not in m.upper()]

    if not markets:
        return None

    # Step 3: Get Prices
    payload_price = payload_base.copy()
    payload_price["count"] = str(len(markets))

    response = http_client.post(URL_PRICE, data=payload_price)
    prices_html = response.text

    # Parse Prices
    parsed_data = parse_price_rows(
        prices_html, markets, region_id, category_name, date_text
    )
    return parsed_data

def parse_price_rows(html_rows, market_list, region_id, category_name, payload_date):
    """
    Parses the price HTML rows into structured dictionaries.
    """
    soup = BeautifulSoup(html_rows, "html.parser")
    parsed_data = []
    rows = soup.find_all("tr")

    # Use extract_dt from payload or current time? 
    # Original code used datetime.now() inside the loop?
    # Actually original code used datetime.now().strftime("%Y-%m-%d") for extract_dt
    
    extract_dt = datetime.now().isoformat()
    
    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        try:
            comm_name = cells[0].get_text(strip=True)
            specs = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            full_commodity_name = f"{comm_name} - {specs}" if specs else comm_name
            price_cells = cells[2:]

            if not price_cells:
                continue

            for idx, price_cell in enumerate(price_cells):
                if idx >= len(market_list):
                    break

                market_name = market_list[idx]
                price_text = price_cell.get_text(strip=True)

                # Skip empty or invalid prices logic (simplified)
                if not price_text or price_text == "-" or "prev" in price_text.lower():
                    continue
                
                # Basic cleaning
                try:
                    price_val = float(price_text.replace(",", ""))
                except ValueError:
                    continue

                record = {
                    "extract_dt": extract_dt,
                    "region_id": region_id,
                    "region_name": REGION_MAP.get(region_id, "Unknown"),
                    "market_name": market_name,
                    "commodity_group": category_name,
                    "commodity_name": full_commodity_name,
                    "price": price_val,
                    "specifications": specs,
                    "raw_date_text": payload_date
                }
                parsed_data.append(record)

        except Exception as e:
            logger.warning(f"Error parsing row: {e}")
            continue

    return parsed_data
