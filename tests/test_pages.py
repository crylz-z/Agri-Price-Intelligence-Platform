"""Smoke tests: the dashboard page renders without an exception on small marts.

`tests/fixtures/marts/` is cut from the real marts (farmer_share_monthly: the
months from Sep 2025, plus national red onion in 2023 for the hook), so these
run offline. Rebuild them if a mart's columns change.
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


def test_the_headlines_tell_the_story_in_order():
    at = render()
    assert not at.exception, at.exception
    assert at.title[0].value == "Who's eating the farmer's peso?"
    assert [h.value for h in at.header][:5] == [
        "In January 2023, onions hit ₱468 a kilo. Farmers got :blue[₱216].",
        "Farmers got :blue[26% less] for tomato this year. You paid 13% more.",
        "Farmers get :blue[46 centavos] of your peso",
        "Traders now take :orange[21 centavos] of your peso, up from 16",
        "Drop ₱10 at the farm, and you save only ₱8",
    ]
    assert at.subheader[-1].value.startswith("Farmers get 46 centavos of your peso.")
    assert at.button(key="theme").label == "Dark"
    at.button(key="theme").click().run()
    assert not at.exception, at.exception


@pytest.mark.parametrize(
    "food",
    [
        "Red onion",
        "Regular rice",
        "Egg",
        "Repolyo",
        "Pechay",
        "Bangus",
        "Pork kasim",
        "Beef with bones",
        "Whole chicken",
    ],
)
def test_check_your_food_renders_each_kind_of_food(food):
    at = render(food=food)
    assert not at.exception, at.exception
    assert at.selectbox[0].value == food


def test_lines_under_the_headlines_say_how_to_read_each_chart():
    at = render()
    lines = [m.value for m in at.markdown]
    assert any("crashed to ₱65. The **store price** was still ₱220" in v for v in lines)
    assert any("lowest first: carrot gets 23" in v for v in lines)
    assert any("Most foods, 14 of 16, come down slower" in v for v in lines)
    assert any(c.value.startswith(":material/science: An example") for c in at.caption)
    assert food_metrics(at)[2:] == ["Traders", "Stores"]


def food_metrics(at: AppTest) -> list[str]:
    """The metric labels in "Check your food", after the big story numbers."""
    labels = [m.label for m in at.metric]
    return labels[next(i for i, x in enumerate(labels) if x.startswith("You pay")) :]


def test_each_story_section_opens_with_its_big_numbers():
    at = render()
    heroes = [(m.label, m.value) for m in at.metric][:8]
    assert heroes == [
        ("Onions in the store, Jan 2023", "₱468"),
        ("The farmer got", ":blue[₱216]"),
        ("Farm price, tomato", ":blue[−26%]"),
        ("Store price, tomato", "+13%"),
        ("The farmer's part of a peso", ":blue[46¢]"),
        ("Traders' part of a peso, 2018", "16¢"),
        ("Now", ":orange[21¢]"),
        ("Of a ₱10 farm drop, you see", "₱8"),
    ]


def echarts(at: AppTest) -> list[dict]:
    """Each ECharts chart's option, in page order: hook, year, peso, dots,
    middle, ratchet."""
    return [json.loads(element.proto.spec) for element in at.get("echarts_chart")]


def test_the_hook_shades_the_gap_between_farm_and_store_in_amber():
    hook = echarts(render())[0]
    names = [s["name"] for s in hook["series"]]
    assert names == ["base", "store price", "the gap", "farm price"]
    assert hook["xAxis"]["data"] == ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    assert hook["series"][2]["areaStyle"]["color"] == views.AMBER
    store, farm = hook["series"][views.STORE_SLOT], hook["series"][3]
    assert farm["color"] == views.FARM and "color" not in store
    labelled = [p["label"]["formatter"] for p in farm["data"] if p["label"]["show"]]
    assert labelled == ["₱216", "₱65"]


def test_the_year_chart_puts_farm_down_store_up_on_top_with_meat_and_fish():
    year = echarts(render())[1]
    foods = year["yAxis"]["data"]
    assert foods[:2] == ["Tomato", "Ampalaya"]
    assert {"Pork kasim", "Beef with bones", "Bangus"} <= set(foods)
    assert "Repolyo" not in foods
    farm, store = year["series"]
    assert farm["data"][0]["label"]["formatter"] == "−26%"
    assert year["series"].index(store) == views.STORE_SLOT
    assert not any("itemStyle" in d for d in store["data"])
    pork = foods.index("Pork kasim")
    assert store["data"][pork]["label"]["formatter"] == "−10%"


def test_the_middle_chart_joins_each_foods_farm_and_store_growth():
    middle = echarts(render())[4]
    foods = middle["yAxis"]["data"]
    assert len(foods) == 25 and foods[0] == "Red onion"
    bars, store, farm = middle["series"]
    assert "itemStyle" not in store
    ratchet = echarts(render())[5]
    assert [s.get("color") for s in ratchet["series"]] == [None, None]
    links = bars["markLine"]["data"]
    assert sum(link[0]["lineStyle"]["color"] == views.AMBER for link in links) == 19
    onion = farm["data"][0]
    assert onion["label"]["formatter"] == "−17%"
    assert store["data"][0]["label"]["formatter"] == "+48%"
    hollow = {
        foods[i] for i, d in enumerate(farm["data"]) if d["symbol"] == "emptyCircle"
    }
    assert hollow == {"Pork kasim", "Pork liempo", "Whole chicken", "Beef with bones"}
    assert store["markLine"]["label"]["formatter"] == "Inflation +33%"


def test_every_chart_has_a_so_what_line_and_no_public_record():
    at = render(food="Red onion")
    assert not at.exception, at.exception
    so_whats = [m.value for m in at.markdown if ":material/lightbulb:" in m.value]
    assert len(so_whats) == 6
    assert "farmers got only 46 centavos of every peso" in so_whats[0]
    assert "that fell to 30" in so_whats[0]
    assert "for 6 of 10 foods, the farmer's drop never reached you" in so_whats[1]
    assert "54 centavos, 21 to traders and 33 to stores" in so_whats[2]
    assert "for 19 of 25 foods, the store price grew faster" in so_whats[3]
    assert "the store price is ₱6 higher" in so_whats[4]
    assert so_whats[5].startswith(":material/lightbulb: So red onion's farmer gets")
    assert not any(s.value == "On the record" for s in at.subheader)


def test_the_public_record_shows_only_when_switched_on(monkeypatch):
    monkeypatch.setattr(views, "SHOW_RECORD", True)
    at = render()
    assert not at.exception, at.exception
    assert any(s.value == "On the record" for s in at.subheader)
    assert any(
        "Philippine Competition Commission found" in m.value for m in at.markdown
    )


def test_a_food_without_wholesale_shows_one_gap():
    at = render(food="Kangkong")
    assert not at.exception, at.exception
    assert food_metrics(at)[2:] == ["The gap"]


def test_fish_shows_its_quarter_and_its_farmer_share():
    at = render(food="Bangus")
    assert not at.exception, at.exception
    assert any(c.value == "July–September 2026, national average." for c in at.caption)
    so_whats = [m.value for m in at.markdown if ":material/lightbulb:" in m.value]
    assert so_whats[-1].endswith(
        "bangus's farmer gets 59 centavos of every peso you pay, more than the typical 46."
    )


def test_the_typical_peso_adds_up_and_every_food_gets_a_dot():
    charts = echarts(render())
    assert len(charts) == 6
    peso, dots = charts[2], charts[3]
    assert [s["data"][0] for s in peso["series"]] == [46, 21, 33]
    assert [s["itemStyle"]["color"] for s in peso["series"]] == [
        views.FARM,
        views.AMBER,
        views.STORE_GREY,
    ]
    assert "Average of the 20 foods" in peso["tooltip"]["formatter"]
    assert len(dots["yAxis"][0]["data"]) == 21
    assert dots["yAxis"][0]["data"][0] == "Carrot"
    assert dots["yAxis"][1]["data"][0] == "23"
    for spec in charts:
        assert spec["animationDuration"] <= 1000
        assert "function" not in json.dumps(spec)


def test_no_sentence_on_the_page_starts_with_a_numeral():
    at = render(food="Red onion")
    texts = [e.value for e in (*at.header, *at.subheader, *at.markdown, *at.caption)]
    for text in texts:
        plain = re.sub(r":material/\w+:|:\w+\[|\*\*|\]", "", text).strip()
        for sentence in re.split(r"(?<=[.!?])\s+", plain):
            assert not re.match(r"[₱+\-]?\d", sentence), (sentence, text)


def test_the_theme_colours_words_like_the_charts_in_both_modes():
    """A coloured word, a big number and a bar share one colour per role, and
    the store price, left uncoloured in the STORE_SLOT, takes each mode's text
    colour from the theme's chart palette."""
    config = tomllib.loads(
        (Path(__file__).parents[1] / ".streamlit" / "config.toml").read_text("utf-8")
    )
    for mode in ("light", "dark"):
        theme = config["theme"][mode]
        assert theme["blueColor"] == theme["blueTextColor"] == views.FARM
        assert theme["orangeColor"] == theme["orangeTextColor"] == views.AMBER
        palette = theme["chartCategoricalColors"]
        assert palette[0] == views.FARM and palette[2] == views.AMBER
        assert palette[views.STORE_SLOT] == theme["textColor"]


def test_meat_shows_both_prices_and_how_each_moved_never_a_share():
    at = render(food="Pork kasim")
    assert not at.exception, at.exception
    assert food_metrics(at) == ["You pay, per kg kasim", "Farm price, per kg live hog"]
    lines = [m.value for m in at.markdown]
    assert any(
        "the :blue[**live hog price**] fell 19%; **kasim** fell 10%." in v
        for v in lines
    )
    so_whats = [v for v in lines if ":material/lightbulb:" in v]
    assert so_whats[-1].endswith(
        "what you pay for kasim rose 40%, but the live hog price rose 24%."
    )
    assert not any("centavos of every peso you pay" in v for v in so_whats[-1:])
    beef = render(food="Beef with bones")
    assert food_metrics(beef) == [
        "You pay, per kg beef",
        "Farm price, per kg live cattle",
    ]
