import dlt
import requests
import concurrent.futures
from datetime import datetime
from typing import Iterator, Dict, Any, List, Optional
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.core.config import REGION_MAP, CATEGORY_MAP, BASE_URL
from src.core.http_client import AgriHttpClient
from src.core.logger import get_logger

logger = get_logger(__name__)

# Constants
URL_DATE = f"{BASE_URL}/tbl_price_get_date_rice.php"
URL_HEADER = f"{BASE_URL}/tbl_price_get_comm_header.php"
URL_PRICE = f"{BASE_URL}/tbl_price_get_comm_price.php"


@dlt.source
def agri_price_source(limit: Optional[int] = None):
    """
    dlt source entrypoint. Delegates to the resource generator.
    The `limit` parameter is used for testing to restrict the number of region/category combinations.
    """
    return agri_price_resource(limit=limit)


@dlt.resource(write_disposition="append")
def agri_price_resource(limit: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    """
    Yields structured price records by scraping the DA Bantay Presyo website.
    Iterates over all 17 regions × 10 commodity categories (170 combinations).
    Uses ThreadPoolExecutor to drastically reduce extraction time via concurrency.
    """
    http_client = AgriHttpClient()
    count = 0
    futures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for region_id, region_name in REGION_MAP.items():
            for category_id, category_name in CATEGORY_MAP.items():
                if limit and len(futures) >= limit:
                    break
                futures.append(
                    executor.submit(
                        fetch_single_category,
                        http_client,
                        region_id,
                        region_name,
                        category_id,
                        category_name,
                    )
                )
            if limit and len(futures) >= limit:
                break

        for future in concurrent.futures.as_completed(futures):
            # Errors are gracefully caught inside fetch_single_category,
            # so data will be None if exhaustive retries failed.
            data = future.result()
            if data:
                yield from data
                count += 1


def fetch_single_category(
    http_client, region_id, region_name, category_id, category_name
) -> Optional[List[Dict[str, Any]]]:
    """Helper function to execute HTTP fetches and handle specific combination logging."""
    logger.info(f"Extracting: {region_name} - {category_name}")
    try:
        return fetch_category_data(http_client, region_id, category_id, category_name)
    except Exception as e:
        logger.error(
            f"Skipping {region_name} - {category_name} after all retries exhausted",
            error=str(e),
        )
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(
        (requests.exceptions.RequestException, requests.exceptions.HTTPError)
    ),
)
def fetch_category_data(
    http_client, region_id, category_id, category_name
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches and parses price data for a single region/category combination.
    Executes three sequential HTTP POST requests against the DA Bantay Presyo API:
      1. Retrieve the data publication date for the given region/category.
      2. Retrieve the market column headers (market names).
      3. Retrieve the price rows, using the market count from step 2.
    Returns a list of structured price records, or None if no markets are found.
    """
    payload_base = {"region": region_id, "commodity": category_id}

    # Step 1: Retrieve the publication date for this region/category combination.
    response = http_client.post(URL_DATE, data=payload_base, timeout=15)
    date_text = response.text

    # Step 2: Retrieve market column headers to determine which markets are reporting.
    response = http_client.post(URL_HEADER, data=payload_base, timeout=15)
    headers_html = response.text

    soup = BeautifulSoup(headers_html, "html.parser")
    markets = [
        td.get_text(strip=True) for td in soup.find_all("td", class_="text-wrap")
    ]
    # Exclude the 'SPECIFICATIONS' header column — it is a label, not a market name.
    markets = [m for m in markets if m and "SPECIFICATIONS" not in m.upper()]

    if not markets:
        # No markets reporting for this combination; skip silently.
        return None

    # Step 3: Retrieve price rows, passing the market count so the server returns the correct columns.
    payload_price = payload_base.copy()
    payload_price["count"] = str(len(markets))

    response = http_client.post(URL_PRICE, data=payload_price, timeout=15)
    prices_html = response.text

    return parse_price_rows(prices_html, markets, region_id, category_name, date_text)


def parse_price_rows(html_rows, market_list, region_id, category_name, payload_date):
    """
    Parses the price HTML table rows returned by the DA Bantay Presyo API into
    structured dictionaries ready for dlt ingestion.

    Each row represents a commodity. Columns 0-1 are commodity name and specifications;
    columns 2+ are per-market prices aligned to `market_list` by index.
    """
    soup = BeautifulSoup(html_rows, "html.parser")
    parsed_data = []
    rows = soup.find_all("tr")

    # Capture extraction timestamp once per batch to ensure consistency across all records
    # in this region/category combination.
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

                # Skip cells that are empty, placeholder dashes, or carry-forward indicators.
                if not price_text or price_text == "-" or "prev" in price_text.lower():
                    continue

                try:
                    price_val = float(price_text.replace(",", ""))
                except ValueError:
                    # Non-numeric cell content; skip without raising.
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
                    "raw_date_text": payload_date,
                }
                parsed_data.append(record)

        except Exception as e:
            logger.warning(f"Error parsing row: {e}")
            continue

    return parsed_data
