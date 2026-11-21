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

from src.dashboard import context, data, views

MARTS = Path(__file__).parent / "fixtures" / "marts"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(
        data, "load", lambda path: pd.read_parquet(MARTS / Path(path).name)
    )


def render(guess: int | None = 150, **params: str) -> AppTest:
    """The page with the hook already answered (a guess of ₱150), unless
    `guess` is None: then it shows as a reader first sees it."""
    at = AppTest.from_string(
        "from src.dashboard.views import case_page\ncase_page()", default_timeout=60
    )
    if guess is not None:
        at.session_state[views.HOOK_GUESS] = guess
    for key, value in params.items():
        at.query_params[key] = value
    return at.run()


def test_the_hook_asks_for_a_guess_before_it_shows_the_store_price():
    at = render(guess=None)
    assert not at.exception, at.exception
    assert at.header[0].value == (
        "In March 2023, farmers got :blue[₱65] for a kilo of onions. What do you "
        "think stores charged?"
    )
    assert [(m.label, m.value) for m in at.metric][:1] == [
        ("Farmers got, Mar 2023", ":blue[₱65]")
    ]
    assert at.metric[1].label != "Stores charged"
    assert not any("₱220" in m.value for m in at.markdown)
    slider = at.slider(key="hook_slider")
    assert (slider.min, slider.max, slider.step) == (65, 450, 5)
    slider.set_value(150)
    at.button(key="hook_show").click().run()
    assert not at.exception, at.exception
    assert at.header[0].value.endswith("Where did the :orange[₱155] go?")
    assert at.metric[1].label == "Stores charged"
    lines = [m.value for m in at.markdown]
    assert "Your guess was ₱150. Stores charged ₱220, ₱70 more." in lines
    assert not at.slider


def test_who_got_caught_opens_on_the_fine_and_shows_each_case_as_a_card():
    at = render()
    fine = next(m for m in at.metric if m.label.startswith("Fined so far"))
    assert (fine.label, fine.value) == (
        "Fined so far, Oct 2026",
        ":orange[₱1.76 billion]",
    )
    lines = [m.value for m in at.markdown]
    badges = [v for v in lines if "-badge[" in v]
    assert badges == [
        ":gray-badge[:material/gavel: Ruling]",
        ":gray-badge[:material/description: Charged]",
        ":gray-badge[:material/search: Finding]",
        ":gray-badge[:material/record_voice_over: Alleged]",
    ]


def test_what_can_be_done_has_titled_cards_and_a_report_button():
    at = render()
    button = at.get("link_button")[0]
    assert button.proto.label == "Report a cartel to the PCC"
    assert button.proto.url == context.PCC_PORTAL
    lines = [m.value for m in at.markdown]
    for title, icon, fact in context.BEING_DONE:
        assert f"**:material/{icon}: {title}**" in lines
        assert f"{fact.text} {views.cite(fact)}" in lines


def test_the_headlines_tell_the_story_in_order():
    at = render()
    assert not at.exception, at.exception
    assert at.title[0].value == "Who's eating the farmer's peso?"
    assert [h.value for h in at.header] == [
        "In March 2023, farmers got :blue[₱65] for a kilo of onions. Stores charged "
        "₱220. Where did the :orange[₱155] go?",
        "Between the farmer and you: traders, wholesalers and stores",
        "Farmers get :blue[46 centavos] of your peso",
        "Traders now take :orange[21 centavos] of your peso, up from 16",
        "Drop ₱10 at the farm, and you save only ₱8",
        "Who got caught",
        "What can be done",
        "Check your food",
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
    assert any("from ₱216 in January to ₱65 by March" in v for v in lines)
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
    heroes = [(m.label, m.value) for m in at.metric][:6]
    # Traders' part has one number on the page, section 4's (owner, 2026-11-21).
    assert heroes == [
        ("Farmers got, Mar 2023", ":blue[₱65]"),
        ("Stores charged", "₱220"),
        ("The farmer's part of a peso", ":blue[46¢]"),
        ("Traders' part of a peso, 2018", "16¢"),
        ("Now", ":orange[21¢]"),
        ("Of a ₱10 farm drop, you see", "₱8"),
    ]


def echarts(at: AppTest) -> list[dict]:
    """Each ECharts chart's option, in page order: hook, dots, middle, ratchet."""
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


def test_the_middle_chart_joins_each_foods_farm_and_store_growth():
    middle = echarts(render())[2]
    foods = middle["yAxis"]["data"]
    assert len(foods) == 25 and foods[0] == "Red onion"
    bars, store, farm = middle["series"]
    assert "itemStyle" not in store
    ratchet = echarts(render())[3]
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


def test_every_chart_has_a_so_what_line():
    at = render(food="Red onion")
    assert not at.exception, at.exception
    so_whats = [m.value for m in at.markdown if ":material/lightbulb:" in m.value]
    # The ratchet's so-what waits for the reader's first press.
    assert len(so_whats) == 5
    assert "farmers got only 30 centavos of every peso" in so_whats[0]
    assert "January's peak, they got 46" in so_whats[0]
    assert "farmers and fisherfolk are among the poorest" in so_whats[1]
    assert so_whats[2].endswith(
        "So more than half your peso, 54 centavos, is spent after the farm, by "
        "traders and stores."
    )
    assert "for 19 of 25 foods, the store price grew faster" in so_whats[3]
    assert so_whats[4].startswith(":material/lightbulb: So red onion's farmer gets")


def test_the_public_record_is_on_the_page_rulings_first_each_sourced():
    at = render()
    assert not at.exception, at.exception
    record = data.load_suspects()
    record = record[record["role"] == "suspect"]
    lines = [m.value for m in at.markdown]
    places = []
    for row in record.itertuples():
        matches = [i for i, line in enumerate(lines) if row.claim in line]
        assert len(matches) == 1, row.claim
        line = lines[matches[0]]
        assert f"]({row.source_url})" in line
        assert f"{row.source_date:%d %b %Y}" in line
        places.append(matches[0])
    assert places == sorted(places)
    assert "Philippine Competition Commission" in lines[places[0]]
    assert not any("opinion" in line.lower() for line in lines)


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


def test_the_receipt_adds_up_and_every_food_gets_a_dot():
    at = render()
    receipt = at.table[0].value
    assert list(receipt.columns) == [
        "You pay",
        ":blue[Farmer]",
        ":orange[Traders]",
        "Stores",
    ]
    assert receipt.loc["Galunggong, 1 kg"].tolist() == ["₱237", "₱128", "₱51", "₱58"]
    assert receipt.loc["**Total**"].tolist() == [
        "**₱575**",
        "**₱301**",
        "**₱120**",
        "**₱154**",
    ]
    assert any(
        c.value.startswith(":material/receipt_long: An example basket")
        and "galunggong July–September 2026" in c.value
        for c in at.caption
    )
    charts = echarts(at)
    assert len(charts) == 4
    dots = charts[1]
    assert len(dots["yAxis"][0]["data"]) == 21
    assert dots["yAxis"][0]["data"][0] == "Carrot"
    assert dots["yAxis"][1]["data"][0] == "23"
    for spec in charts:
        assert spec["animationDuration"] <= 1000
        assert "function" not in json.dumps(spec)


def test_every_series_eases_like_its_chart():
    # ECharts gives a line series its own linear easing, which overrides the
    # chart's: the hook's line crept at full speed to a dead stop (ticket 08).
    for spec in echarts(render(food="Red onion")):
        for series in spec["series"]:
            assert series["animationEasing"] == spec["animationEasing"], series


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


def test_headings_carry_no_link_so_the_page_always_opens_at_the_top():
    """A heading's link icon puts "#<heading>" in the address bar, and the
    browser then reopens the page scrolled to that heading."""
    at = render()
    headings = [*at.title, *at.header, *at.subheader]
    assert headings and all(h.proto.hide_anchor for h in headings)


def test_the_chain_names_each_step_and_cites_every_fact():
    """Section 2: four steps from farm to store, then what a fair cut pays for,
    each fact followed by a link to its source."""
    at = render()
    lines = [m.value for m in at.markdown]
    titles = [v for v in lines if v.startswith("**:material/") and v.endswith("**")]
    steps = titles[:4]  # section 7's cards follow, titled the same way
    assert [s.split("**")[1].split(" ", 1)[1] for s in steps] == [
        "Farmer",
        "Trader",
        "Wholesaler",
        "Store",
    ]
    arrows = [i for i, v in enumerate(lines) if v == views.CHAIN_ARROW]
    first = lines.index(steps[0])
    assert arrows == [first + 2, first + 5, first + 8]  # one between each step
    page = " ".join(lines)
    for fact in context.facts():
        assert f"{fact.text} {views.cite(fact)}" in page
    assert views.cite(context.SPOILAGE) == (
        ":gray[([JESAM, UPLB, 2019](https://ovcre.uplb.edu.ph/journals-uplb/index.php"
        "/JESAM/article/download/89/69))]"
    )


def test_the_reader_plays_the_ratchet():
    at = render()
    farm, store = echarts(at)[3]["series"]
    assert len(farm["data"]) == 1 and len(store["data"]) == 1
    assert at.button(key="ratchet_reset").disabled
    at.button(key="ratchet_up").click().run()
    assert any("kept pace" in m.value for m in at.markdown)
    at.button(key="ratchet_down").click().run()
    assert not at.exception, at.exception
    farm, store = echarts(at)[3]["series"]
    assert [p[1] for p in farm["data"]] == [0, 10, 0]
    assert farm["endLabel"]["formatter"] == "back to start"
    assert store["endLabel"]["formatter"] == "+₱2"
    assert any(
        "the farm price is back where it started, but the store price is ₱2 "
        "higher. You pay ₱2 the farmer never saw." in m.value
        for m in at.markdown
    )
    at.button(key="ratchet_reset").click().run()
    assert len(echarts(at)[3]["series"][0]["data"]) == 1
