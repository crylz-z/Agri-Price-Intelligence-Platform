import dlt
import concurrent.futures
import time
import random
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Iterator, Dict, Any, List, Optional
from bs4 import BeautifulSoup

from src.core.config import REGION_MAP, BASE_URL
from src.core.http_client import AgriHttpClient
from src.core.logger import get_logger

logger = get_logger(__name__)

# Constants
URL_DATE = f"{BASE_URL}/tbl_price_get_date_rice.php"
URL_HEADER = f"{BASE_URL}/tbl_price_get_comm_header.php"
URL_PRICE = f"{BASE_URL}/tbl_price_get_comm_price.php"

REGION_FAILURES = {}
REGION_STATS = {}
GLOBAL_STATE = {"failures": 0, "max_failures": 6}
STATE_LOCK = threading.Lock()


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
    futures = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for region_id, region_name in REGION_MAP.items():
            if region_name not in REGION_STATS:
                REGION_STATS[region_name] = {"rows": 0, "status": "OK", "duration": 0.0}

            if REGION_FAILURES.get(region_name, 0) >= 2:
                REGION_STATS[region_name]["status"] = "SKIPPED (DEGRADED)"
                continue

            if limit and len(futures) >= limit:
                break
            future = executor.submit(
                fetch_region_all_commodities,
                http_client,
                region_id,
                region_name,
            )
            futures[future] = region_name

        for future in concurrent.futures.as_completed(futures):
            task_label = futures[future]
            base_region = task_label

            try:
                data, duration = future.result()
                REGION_STATS[base_region]["duration"] += duration
                if data:
                    REGION_FAILURES[base_region] = 0
                    with STATE_LOCK:
                        GLOBAL_STATE["failures"] = max(
                            0, GLOBAL_STATE["failures"] - 0.5
                        )
                    REGION_STATS[base_region]["rows"] += len(data)
                    yield from data
                    count += 1
            except Exception as e:
                logger.error(f"Task failed for {task_label}: {e}")
                REGION_FAILURES[base_region] = REGION_FAILURES.get(base_region, 0) + 1
                with STATE_LOCK:
                    GLOBAL_STATE["failures"] += 1
                REGION_STATS[base_region]["status"] = "ERROR"

    skipped = [
        reg for reg, stats in REGION_STATS.items() if "SKIPPED" in stats["status"]
    ]
    logger.info(
        "Extraction cycle complete.",
        total_rows=sum(s["rows"] for s in REGION_STATS.values()),
        regions_processed=len(REGION_STATS),
        regions_skipped=len(skipped),
        skipped_details=skipped if skipped else None,
    )
    summarize_extraction()


def summarize_extraction():
    """
    Prints a human-readable professional summary table of the extraction cycle.
    Includes regional breakdown of rows, duration, and final status.
    """
    print("\n" + "=" * 95)
    print(f"{'REGION':<55} | {'ROWS':<8} | {'SEC':<8} | {'STATUS'}")
    print("-" * 95)

    sorted_stats = sorted(
        REGION_STATS.items(), key=lambda x: x[1]["rows"], reverse=True
    )
    total_rows = 0
    total_duration = 0

    for region, stats in sorted_stats:
        status = stats["status"]
        rows = stats["rows"]
        duration = stats["duration"]
        total_rows += rows
        total_duration += duration
        print(f"{region:<55} | {rows:<8} | {duration:<8.2f} | {status}")

    print("-" * 95)
    print(
        f"{'TOTAL (Parallel Service Time)':<55} | {total_rows:<8} | {total_duration:<8.2f}"
    )
    print("=" * 95 + "\n")


def fetch_region_all_commodities(
    http_client, region_id, region_name
) -> tuple[List[Dict[str, Any]], float]:
    """Helper function to execute HTTP fetches with timing metrics."""
    start = time.time()

    with STATE_LOCK:
        if GLOBAL_STATE["failures"] >= GLOBAL_STATE["max_failures"]:
            logger.warning(f"Global failure limit reached. Fast-failing {region_name}.")
            return [], time.time() - start

    if REGION_FAILURES.get(region_name, 0) >= 2:
        return [], time.time() - start

    logger.info(f"Extracting: {region_name}")
    try:
        data = fetch_region_data(http_client, region_id, region_name)
    except Exception as e:
        raise e
    return data if data else [], time.time() - start


def fetch_region_data(
    http_client, region_id, region_name
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches and parses price data for a single region (ALL categories at once).
    Executes three sequential HTTP POST requests against the DA Bantay Presyo API:
      1. Retrieve the data publication date for the given region.
      2. Retrieve the market column headers (market names).
      3. Retrieve the price rows, using the market count from step 2.
    Returns a list of structured price records, or None if no markets are found.
    """
    # Empty commodity ID requests all categories simultaneously
    payload_base = {"region": region_id, "commodity": ""}

    # Add significant jitter to disguise automated polling intervals
    time.sleep(random.uniform(2.0, 5.0))

    response = http_client.post(URL_DATE, data=payload_base)
    date_text = response.text

    response = http_client.post(URL_HEADER, data=payload_base)
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

    response = http_client.post(URL_PRICE, data=payload_price)
    prices_html = response.text

    return parse_price_rows(prices_html, markets, region_id, date_text)


def parse_price_rows(html_rows, market_list, region_id, payload_date):
    """
    Parses the price HTML table rows returned by the DA Bantay Presyo API into
    structured dictionaries ready for dlt ingestion.

    Dynamically infers the `commodity_group` (category) by detecting header rows
    spanning the entire table.
    """
    soup = BeautifulSoup(html_rows, "html.parser")
    parsed_data = []
    rows = soup.find_all("tr")

    extract_dt = datetime.now(ZoneInfo("Asia/Manila")).isoformat()
    current_category = "All Commodities"

    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        # Detect category header row (frequently DA uses single colspan cell)
        if len(cells) == 1 or cells[0].has_attr("colspan"):
            text = cells[0].get_text(strip=True)
            if text and "SPECIFICATIONS" not in text.upper():
                # Title case the category (e.g. "LOWLAND VEGETABLES" -> "Lowland Vegetables")
                current_category = text.title()
            continue

        try:
            comm_name = cells[0].get_text(strip=True)
            if not comm_name:
                continue

            specs = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            full_commodity_name = f"{comm_name} - {specs}" if specs else comm_name
            price_cells = cells[2:]

            if not price_cells:
                # Could be a category header row posing as a normal row
                if comm_name and not specs and "SPECIFICATION" not in comm_name.upper():
                    current_category = comm_name.title()
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
                    "commodity_group": current_category,
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
