from datetime import date
from pathlib import Path

import pytest
import requests

from src.core.config import CATEGORY_MAP, REGION_MAP
from src.etl import scraper

FIXTURES = Path(__file__).parent / "fixtures"
# Saved from NCR (130000000), category 8 "Meat and Poultry", posted 2026-10-28.
DATE_HTML = (FIXTURES / "date.html").read_text()
HEADER_HTML = (FIXTURES / "header.html").read_text()
PRICE_HTML = (FIXTURES / "price.html").read_text()


def test_parse_posting_date_strips_whitespace():
    assert scraper.parse_posting_date(DATE_HTML) == date(2026, 10, 28)


def test_parse_posting_date_rejects_garbage():
    with pytest.raises(ValueError):
        scraper.parse_posting_date("No data available")


def test_parse_markets_skips_label_columns():
    markets = scraper.parse_markets(HEADER_HTML)
    assert len(markets) == 38
    assert markets[0] == "COMMONWEALTH MARKET"
    assert not any("SPECIFICATIONS" in m or "COMMODITY" in m for m in markets)


def test_parse_markets_labels_repeated_names():
    # Region III lists some markets twice, each column with its own prices.
    html = "".join(
        f'<th class="text-wrap">{m}</th>' for m in ["BALER", "TARLAC", "BALER"]
    )
    assert scraper.parse_markets(html) == ["BALER", "TARLAC", "BALER #2"]


def test_parse_price_rows_skips_na_cells():
    rows = scraper.parse_price_rows(PRICE_HTML, scraper.parse_markets(HEADER_HTML))
    # 17 commodities x 38 markets, minus 319 "N/A" cells
    assert len(rows) == 17 * 38 - 319
    assert rows[0] == (
        "Beef Brisket - MEAT WITH BONES",
        "MEAT WITH BONES",
        "COMMONWEALTH MARKET",
        400.0,
    )
    assert all(price > 0 for *_, price in rows)


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        pass


class FakeSession:
    """Serves the fixtures for every region/category, except the given failures."""

    def __init__(self, fail_regions=(), fail_categories=()):
        self.fail_regions = set(fail_regions)
        self.fail_categories = set(fail_categories)
        self.calls = 0

    def post(self, url, data, timeout):
        self.calls += 1
        if data["region"] in self.fail_regions or (
            "date" not in url and data["commodity"] in self.fail_categories
        ):
            raise requests.ConnectionError("boom")
        if "date" in url:
            return FakeResponse(DATE_HTML)
        return FakeResponse(HEADER_HTML if "header" in url else PRICE_HTML)


def test_scrape_builds_records_with_posting_date():
    result = scraper.scrape(FakeSession(), regions={"130000000": "NCR"}, delay=0)
    assert result.failures == []
    assert len(result.records) == len(CATEGORY_MAP) * (17 * 38 - 319)
    first = result.records[0]
    assert first["region_id"] == "130000000"
    assert first["region_name"] == "NCR"
    assert first["commodity_group"] == "Rice"
    assert first["posting_date"] == date(2026, 10, 28)
    assert first["raw_date_text"] == "October 28, 2026"
    assert str(first["extract_dt"].tzinfo) == "Asia/Manila"


def test_failed_category_does_not_fail_region():
    result = scraper.scrape(
        FakeSession(fail_categories={"3"}), regions={"130000000": "NCR"}, delay=0
    )
    assert len(result.failures) == 1 and "Legumes" in result.failures[0]
    groups = {r["commodity_group"] for r in result.records}
    assert groups == set(CATEGORY_MAP.values()) - {"Legumes"}


def test_failed_region_is_counted_and_others_continue():
    result = scraper.scrape(
        FakeSession(fail_regions={"140000000"}),
        regions={k: REGION_MAP[k] for k in ["130000000", "140000000", "010000000"]},
        delay=0,
    )
    assert len(result.failures) == 1
    assert {r["region_id"] for r in result.records} == {"130000000", "010000000"}


def test_circuit_breaker_stops_when_site_is_down():
    session = FakeSession(fail_regions=set(REGION_MAP))
    result = scraper.scrape(session, regions=REGION_MAP, delay=0)
    assert result.records == []
    assert session.calls == scraper.MAX_CONSECUTIVE_FAILURES
    assert len(result.failures) == len(REGION_MAP)


def test_session_identifies_itself_honestly():
    ua = scraper.make_session().headers["User-Agent"]
    assert ua.startswith("apip/") and "github.com/crylz-z" in ua
