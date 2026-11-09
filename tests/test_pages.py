"""Smoke tests: the dashboard page renders without an exception on small marts.

`tests/fixtures/marts/` is cut from the real marts (14 months; provinces only for
the last 2), so these run offline. Rebuild them if a mart's columns change.
"""

import json
import re
import tomllib
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.dashboard import data, views

MARTS = Path(__file__).parent / "fixtures" / "marts"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(
        data, "load", lambda path: pd.read_parquet(MARTS / Path(path).name)
    )


def render(**params: str) -> AppTest:
    at = AppTest.from_string(
        "from src.dashboard.views import case_page\ncase_page()", default_timeout=60
    )
    for key, value in params.items():
        at.query_params[key] = value
    return at.run()


def test_page_leads_with_the_farmers_share():
    at = render()
    assert not at.exception, at.exception
    assert at.title[0].value == "Who's eating the farmer's peso?"
    assert [h.value for h in at.header][:4] == [
        "Farmers got :blue[26% less] for tomato this year. You paid :orange[13% more].",
        "Farmers get :blue[44 centavos] of your peso",
        "Drop ₱10 at the farm, and you save only :orange[₱8]",
        "The gap grew faster than inflation for :orange[14 of 18] foods",
    ]
    assert at.button(key="theme").label == "Dark"
    at.button(key="theme").click().run()
    assert not at.exception, at.exception


@pytest.mark.parametrize(
    "food", ["Red onion", "Regular rice", "Egg", "Repolyo", "Pechay", "Pork kasim"]
)
def test_check_your_food_renders_each_kind_of_food(food):
    at = render(food=food)
    assert not at.exception, at.exception
    assert at.selectbox[0].value == food


def test_wholesale_splits_the_gap_and_diesel_sits_beside_inflation():
    at = render()
    lines = [m.value for m in at.markdown]
    assert any("lowest first: carrot gets 23" in v for v in lines)
    assert any("Most foods, 14 of 16, come down slower" in v for v in lines)
    assert any("faster than even diesel" in v for v in lines)
    assert food_metrics(at)[2:] == ["Traders", "Stores"]


def food_metrics(at: AppTest) -> list[str]:
    """The metric labels in "Check your food", after the big story numbers."""
    labels = [m.label for m in at.metric]
    return labels[next(i for i, x in enumerate(labels) if x.startswith("You pay")) :]


def test_each_story_section_opens_with_its_big_numbers():
    at = render()
    heroes = [(m.label, m.value) for m in at.metric][:5]
    assert heroes == [
        ("Farm price, tomato", ":blue[−26%]"),
        ("Store price, tomato", ":orange[+13%]"),
        ("The farmer's part of a peso", ":blue[44¢]"),
        ("Of a ₱10 farm drop, you see", ":orange[₱8]"),
        ("Foods whose gap beat inflation", ":orange[14 of 18]"),
    ]


def test_the_year_chart_puts_farm_down_store_up_on_top_and_keeps_pork():
    year = echarts(render())[0]
    foods = year["yAxis"]["data"]
    assert foods[:2] == ["Tomato", "Ampalaya"]
    assert "Pork kasim" in foods and "Repolyo" not in foods
    farm, store = year["series"]
    assert farm["data"][0]["label"]["formatter"] == "−26%"
    assert store["data"][0]["itemStyle"]["color"] == views.AMBER
    pork = foods.index("Pork kasim")
    assert store["data"][pork]["label"]["formatter"] == "−10%"
    assert store["data"][pork]["itemStyle"]["color"] != views.AMBER


def test_every_chart_has_a_so_what_line_and_no_public_record():
    at = render(food="Red onion")
    assert not at.exception, at.exception
    so_whats = [m.value for m in at.markdown if ":material/lightbulb:" in m.value]
    assert len(so_whats) == 5
    assert "for 4 of 6 foods, the farmer's drop never reached you" in so_whats[0]
    assert "the biggest part goes to stores: about 33 centavos" in so_whats[1]
    assert "the store price is ₱6 higher" in so_whats[2]
    assert "rose from 16 to 21 centavos" in so_whats[3]
    assert so_whats[4].startswith(":material/lightbulb: So red onion's farmer gets")
    assert not at.expander


def test_a_food_without_wholesale_shows_one_gap():
    at = render(food="Kangkong")
    assert not at.exception, at.exception
    assert food_metrics(at)[2:] == ["The gap"]


def echarts(at: AppTest) -> list[dict]:
    """Each ECharts chart's option, in page order: year, peso, dots, ratchet,
    growth."""
    return [json.loads(element.proto.spec) for element in at.get("echarts_chart")]


def test_the_typical_peso_adds_up_and_every_food_gets_a_dot():
    charts = echarts(render())
    assert len(charts) == 5
    peso, dots = charts[1], charts[2]
    assert [s["data"][0] for s in peso["series"]] == [44, 23, 33]
    assert "Average of the 17 foods" in peso["tooltip"]["formatter"]
    assert len(dots["yAxis"][0]["data"]) == 18
    assert dots["yAxis"][0]["data"][0] == "Carrot"
    assert dots["yAxis"][1]["data"][0] == "23"
    for spec in charts:
        assert spec["animationDuration"] <= 1000
        assert "function" not in json.dumps(spec)


def test_no_sentence_on_the_page_starts_with_a_numeral():
    at = render(food="Red onion")
    texts = [e.value for e in (*at.header, *at.markdown, *at.caption)]
    for text in texts:
        plain = re.sub(r":material/\w+:|:\w+\[|\*\*|\]", "", text).strip()
        for sentence in re.split(r"(?<=[.!?])\s+", plain):
            assert not re.match(r"[₱+\-]?\d", sentence), (sentence, text)


def test_the_theme_colours_words_like_the_charts_in_both_modes():
    """A coloured word, a big number and a bar share one colour per role."""
    config = tomllib.loads(
        (Path(__file__).parents[1] / ".streamlit" / "config.toml").read_text("utf-8")
    )
    for mode in ("light", "dark"):
        theme = config["theme"][mode]
        assert theme["blueColor"] == theme["blueTextColor"] == views.FARM
        assert theme["orangeColor"] == theme["orangeTextColor"] == views.AMBER


def test_pork_shows_both_prices_and_how_each_moved_never_a_share():
    at = render(food="Pork kasim")
    assert not at.exception, at.exception
    assert at.selectbox[0].options[-1] == "Pork kasim"
    assert food_metrics(at) == ["You pay, per kg kasim", "A live hog sells for, per kg"]
    lines = [m.value for m in at.markdown]
    assert any(
        "the :blue[**hog price**] fell 19%; :orange[**kasim**] fell 10%." in v
        for v in lines
    )
    so_whats = [v for v in lines if ":material/lightbulb:" in v]
    assert so_whats[-1].endswith(
        "what you pay for kasim rose 40%, but the hog's price rose 24%."
    )
    assert not any("centavos of every peso you pay" in v for v in so_whats)
