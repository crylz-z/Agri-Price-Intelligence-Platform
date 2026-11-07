"""Smoke tests: each dashboard page renders without an exception on small marts.

`tests/fixtures/marts/` is cut from the real marts (14 months; provinces only for
the last 2), so these run offline. Rebuild them if a mart's columns change.
"""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.dashboard import data

MARTS = Path(__file__).parent / "fixtures" / "marts"
PAGES = ["today_page", "places_page", "ulam_page", "seasons_page", "lookup_page"]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(
        data, "load", lambda path: pd.read_parquet(MARTS / Path(path).name)
    )


def render(page: str, **params: str) -> AppTest:
    at = AppTest.from_string(
        f"from src.dashboard.views import {page}\n{page}()", default_timeout=60
    )
    for key, value in params.items():
        at.query_params[key] = value
    return at.run()


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = render(page)
    assert not at.exception, at.exception


def test_this_month_renders_for_a_region():
    at = render("today_page", region="Central Luzon")
    assert not at.exception, at.exception
    assert any("In Central Luzon," in m.value for m in at.markdown)


@pytest.mark.parametrize(
    ("place", "headline"),
    [("Cebu", "In Cebu,"), ("Central Visayas (region)", "In Central Visayas,")],
)
def test_where_you_live_renders_for_a_province_and_a_region(place, headline):
    at = render("places_page", place=place, food="Regular rice")
    assert not at.exception, at.exception
    assert at.title[0].value.startswith(headline)


def test_where_you_live_opens_on_the_place_chosen_on_this_month():
    at = AppTest.from_string(
        "from src.dashboard.views import places_page\nplaces_page()", default_timeout=60
    )
    at.session_state["home"] = "072200000"  # Cebu
    at.run()
    assert not at.exception, at.exception
    assert at.selectbox(key="place").value == "072200000"
