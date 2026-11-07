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
PAGES = ["overview_page", "places_page", "lookup_page"]


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


def test_overview_renders_for_a_region():
    at = render("overview_page", region="Central Luzon")
    assert not at.exception, at.exception
    assert any("In Central Luzon," in m.value for m in at.markdown)


@pytest.mark.parametrize("level", ["Provinces", "Regions"])
def test_compare_places_renders_at_each_level(level):
    at = render("places_page", food="Regular rice", level=level)
    assert not at.exception, at.exception
    assert at.title[0].value.startswith("Regular rice costs most in")


def test_look_up_a_food_renders_for_a_province():
    at = render("lookup_page", where="072200000")
    assert not at.exception, at.exception
