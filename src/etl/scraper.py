"""Scrape DA Bantay Presyo, one region and category at a time.

An honest, polite bot: it names itself in the User-Agent, runs sequentially and
waits a fixed delay after every request. robots.txt returns 404 (checked
2026-10-30), so no path is disallowed.
"""

import time
from dataclasses import dataclass, field
from datetime import date, datetime
from importlib.metadata import version
from typing import Any
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.core.config import (
    BACKOFF_FACTOR,
    BASE_URL,
    CATEGORY_MAP,
    MAX_RETRIES,
    REGION_MAP,
    TIMEOUT_SECONDS,
)
from src.core.logger import get_logger

logger = get_logger(__name__)

# Since the 2026 redesign every category has its own endpoint pair, but the
# *_rice.php pair serves any category id 1-10; an empty id returns nothing.
URL_DATE = f"{BASE_URL}/tbl_price_get_date_rice.php"
URL_HEADER = f"{BASE_URL}/tbl_price_get_comm_header_rice.php"
URL_PRICE = f"{BASE_URL}/tbl_price_get_comm_price_rice.php"

USER_AGENT = (
    f"apip/{version('agri-price-intelligence-platform')} "
    "(+https://github.com/crylz-z/Agri-Price-Intelligence-Platform)"
)
REQUEST_DELAY_SECONDS = 1.0
# Stop the whole run after this many failed requests in a row: the site is down.
MAX_CONSECUTIVE_FAILURES = 6
PHT = ZoneInfo("Asia/Manila")


@dataclass
class ScrapeResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def make_session() -> requests.Session:
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = USER_AGENT
    return session


def parse_posting_date(text: str) -> date:
    """'\\r\\nOctober 28, 2026' -> date(2026, 10, 28); raises ValueError otherwise."""
    return datetime.strptime(text.strip(), "%B %d, %Y").date()


def parse_markets(html: str) -> list[str]:
    """Market names are the <th class="text-wrap"> cells of the header row."""
    soup = BeautifulSoup(html, "html.parser")
    return [
        name
        for cell in soup.find_all(["td", "th"], class_="text-wrap")
        if (name := cell.get_text(strip=True))
    ]


def parse_price_rows(
    html: str, markets: list[str]
) -> list[tuple[str, str, str, float]]:
    """Return (commodity_name, specifications, market_name, price) per priced cell."""
    rows = []
    for tr in BeautifulSoup(html, "html.parser").find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 3 or not cells[0]:
            continue
        name, specs = cells[0], cells[1]
        commodity = f"{name} - {specs}" if specs else name
        for market, text in zip(markets, cells[2:]):
            try:
                price = float(text.replace(",", ""))
            except ValueError:  # "N/A", "-" and other placeholders
                continue
            rows.append((commodity, specs, market, price))
    return rows


def scrape(
    session: requests.Session,
    regions: dict[str, str] = REGION_MAP,
    delay: float = REQUEST_DELAY_SECONDS,
) -> ScrapeResult:
    result = ScrapeResult()
    consecutive_failures = 0

    def post(url: str, region_id: str, category_id: str) -> str:
        nonlocal consecutive_failures
        try:
            response = session.post(
                url,
                data={"region": region_id, "commodity": category_id},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException:
            consecutive_failures += 1
            raise
        finally:
            time.sleep(delay)
        consecutive_failures = 0
        return response.text

    for region_id, region_name in regions.items():
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            result.failures.append(f"{region_name}: skipped, site looks down")
            continue
        try:
            raw_date_text = post(URL_DATE, region_id, "1").strip()
            posting_date = parse_posting_date(raw_date_text)
        except (requests.RequestException, ValueError) as e:
            result.failures.append(f"{region_name}: {e}")
            logger.error("Region failed.", region=region_name, error=str(e))
            continue

        extract_dt = datetime.now(PHT)
        rows_before = len(result.records)
        for category_id, category_name in CATEGORY_MAP.items():
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                break
            try:
                markets = parse_markets(post(URL_HEADER, region_id, category_id))
                if not markets:  # no market reports this category
                    continue
                prices = parse_price_rows(
                    post(URL_PRICE, region_id, category_id), markets
                )
            except requests.RequestException as e:
                result.failures.append(f"{region_name} / {category_name}: {e}")
                logger.warning(
                    "Category failed.", region=region_name, category=category_name
                )
                continue
            result.records.extend(
                {
                    "extract_dt": extract_dt,
                    "region_id": region_id,
                    "region_name": region_name,
                    "market_name": market,
                    "commodity_group": category_name,
                    "commodity_name": commodity,
                    "specifications": specs,
                    "price": price,
                    "raw_date_text": raw_date_text,
                    "posting_date": posting_date,
                }
                for commodity, specs, market, price in prices
            )
        logger.info(
            "Region scraped.",
            region=region_name,
            rows=len(result.records) - rows_before,
            posting_date=str(posting_date),
        )
    return result
