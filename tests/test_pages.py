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

from src.dashboard import context, data, how, nav, views

MARTS = Path(__file__).parent / "fixtures" / "marts"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(
        data, "load", lambda path: pd.read_parquet(MARTS / Path(path).name)
    )


APP = Path(__file__).parents[1] / "src" / "dashboard" / "app.py"


def render(page: str = "story", guess: int | None = 150, **params: str) -> AppTest:
    """One page (`nav.PAGES`) with the hook already answered (a guess of ₱150),
    unless `guess` is None: then it shows as a reader first sees it. Query
    params go on the first run, as a shared link's would."""
    at = AppTest.from_file(str(APP), default_timeout=60)
    if guess is not None:
        at.session_state[views.HOOK_GUESS] = guess
    for key, value in params.items():
        at.query_params[key] = value
    at.run()
    if page != "story" and not params:
        at.switch_page(f"app_pages/{page}.py").run()
    return at


def food(name: str) -> AppTest:
    """The food page with `name` picked, through an old `/?food=` link."""
    return render("food", food=name)


def test_the_hook_asks_for_a_guess_before_it_shows_the_store_price():
    at = render(guess=None)
    assert not at.exception, at.exception
    assert at.header[0].value == (
        "In March 2023, farmers got :blue[₱65] for a kilo of onions. What do you "
        "think stores charged?"
    )
    # Before the guess: no big number, and ₱65 shows once, in the header.
    shown = [e.value for e in (*at.header, *at.markdown, *at.caption)]
    shown += [f"{m.label} {m.value}" for m in at.metric]
    assert sum(text.count("₱65") for text in shown) == 1
    assert not any(m.label.startswith("Farmers got") for m in at.metric)
    assert not any("₱220" in m.value for m in at.markdown)
    slider = at.slider(key="hook_slider")
    assert slider.label == "Drag to guess"
    assert (slider.min, slider.max, slider.step, slider.value) == (0, 450, 5, 0)
    slider.set_value(150)
    at.button(key="hook_show").click().run()
    assert not at.exception, at.exception
    assert at.header[0].value.endswith("Where did the :orange[₱155] go?")
    assert [m.label for m in at.metric][:2] == [
        "Farmers got, Mar 2023",
        "Stores charged",
    ]
    lines = [m.value for m in at.markdown]
    assert (
        "Your guess was ₱150, ₱70 short. The :orange[**shaded gap**] is what "
        "traders and stores kept."
    ) in lines
    assert not at.slider


def test_who_got_caught_opens_on_the_fine_and_shows_each_case_as_a_card():
    at = render("caught")
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
    at = render("caught")
    button = at.get("link_button")[0]
    assert button.proto.label == "Report a cartel to the PCC"
    assert button.proto.url == context.PCC_PORTAL
    lines = [m.value for m in at.markdown]
    for title, icon, fact in context.BEING_DONE:
        assert f"**:material/{icon}: {title}**" in lines
        assert f"{fact.text} {views.cite(fact)}" in lines


def test_the_story_headlines_in_order():
    at = render()
    assert not at.exception, at.exception
    assert at.title[0].value == "Who's eating the farmer's peso?"
    assert [h.value for h in at.header] == [
        "In March 2023, farmers got :blue[₱65] for a kilo of onions. Stores charged "
        "₱220. Where did the :orange[₱155] go?",
        "Between the farmer and you: traders, wholesalers and stores",
        "Farmers get :blue[46 centavos] of your peso",
        "Traders now take :orange[21 centavos], up from 16",
        "Drop ₱10 at the farm, and you save only ₱8",
    ]
    # The ending: the fine, then the link on to the record.
    assert [h.value for h in at.subheader] == [
        "Regulators have fined :orange[₱1.76 billion] so far"
    ]
    assert at.button(key="theme").label == "Dark"
    at.button(key="theme").click().run()
    assert not at.exception, at.exception


def test_who_got_caught_headlines_in_order():
    at = render("caught")
    assert not at.exception, at.exception
    assert [h.value for h in at.header] == [
        "It's not one food, and it's not new",
        "Who got caught",
        "What can be done",
    ]
    assert [h.value for h in at.subheader] == [
        "Carrot farmers get only :blue[23 centavos] of your peso",
        "Since 2018, store prices outran farm prices for :orange[19 of 25 foods]",
        "Being done",
        "Where to report",
    ]
    assert [len(c["yAxis"][0]["data"]) for c in echarts(at)[:1]] == [21]


def test_how_its_built_shows_the_pipeline_and_its_live_numbers():
    at = render("how")
    assert not at.exception, at.exception
    assert [h.value for h in at.header] == ["How it's built"]
    dot = at.get("graphviz_chart")[0].proto.spec
    for step in ("PSA OpenSTAT", "raw", "dbt build", "marts", "This page", "GitHub"):
        assert step in dot, step
    lines = [m.value for m in at.markdown]
    for title, icon, text in how.FACTS:
        assert f"**:material/{icon}: {title}**" in lines and text in lines
    assert [(m.label, m.value) for m in at.metric] == [
        ("Latest PSA release", "06 Nov 2026"),
        ("Foods", "25"),
    ]
    button = at.get("link_button")[0]
    assert (
        button.proto.url
        == how.REPO
        == ("https://github.com/crylz-z/Agri-Price-Intelligence-Platform")
    )


def test_the_story_has_no_dots_or_growth_chart():
    # Both moved to "Who got caught" (spec: Page 1).
    charts = echarts(render())
    assert [len(c["series"]) for c in charts] == [4, 2]  # the hook, the ratchet


def top_level(node) -> list:
    """The page's running text, in order: a plain container's contents (a
    fragment, a reveal, the big numbers) count, a card's, a column's or an
    expander's do not."""
    out = []
    for child in node.children.values():
        if type(child).__name__ != "Block":
            out.append(child)
        elif child.type == "flex_container" and not child.proto.flex_container.border:
            out.extend(top_level(child))
    return out


def words(markdown: str) -> int:
    """Words a reader reads: links shown as their text, icons and colour marks
    dropped."""
    text = re.sub(r"\]\([^)]*\)", "]", markdown)
    text = re.sub(r":material/\w+:|:\w+\[|\*\*|[\[\]()]", " ", text)
    return len(text.split())


@pytest.mark.parametrize("page", ["story", "caught"])
def test_each_headline_has_at_most_one_line_and_one_so_what(page):
    """The word budget (spec): under each headline, one short line at most,
    then at most one so-what; no paragraphs. Tooltips, cards and the Sources
    expander hold the rest."""
    at = render(page)
    sections: list[list[str]] = [[]]
    for element in top_level(at.main):
        kind = type(element).__name__
        if kind in ("Header", "Subheader", "Title"):
            sections.append([])
        elif kind == "Markdown" and element.value != views.CHAIN_ARROW:
            sections[-1].append(element.value)
    for lines in sections:
        so_whats = [v for v in lines if v.startswith(":material/lightbulb:")]
        others = [v for v in lines if v not in so_whats]
        assert len(so_whats) <= 1, lines
        assert len(others) <= 1, lines
        for line in lines:
            assert words(line) <= 30, line


def test_the_hook_chart_dots_only_its_labelled_months():
    hook = echarts(render())[0]
    for line in (hook["series"][1], hook["series"][3]):
        dotted = [p["symbol"] != "none" for p in line["data"]]
        labelled = [p["label"]["show"] for p in line["data"]]
        assert dotted == labelled and any(dotted)


def test_the_story_cites_its_facts_in_a_closed_sources_expander():
    at = render()
    sources = at.expander[0]
    assert sources.label == "Sources" and not sources.proto.expanded
    inside = " ".join(m.value for m in sources.markdown)
    for fact in (
        context.ONION_VS_MEAT,
        *(fact for _, _, fact in context.CHAIN),
        *context.FAIR_CUT,
        context.POVERTY,
    ):
        assert f"{fact.text} {views.cite(fact)}" in inside
    outside = [m.value for m in at.markdown if m.value not in inside]
    assert not any("](http" in v for v in outside)


PAGES = list(nav.PAGES)


@pytest.mark.parametrize("page", PAGES)
def test_every_page_has_the_masthead_and_ends_on_the_next_page(page):
    at = render(page)
    assert not at.exception, at.exception
    assert at.caption[0].value.startswith("Philippines · 25 everyday foods")
    assert at.button(key="theme")
    assert at.caption[-1].value.startswith("Farm, wholesale and store prices: PSA")
    following = nav.after(page)
    assert at.page_link[-1].value == f"{views.NEXT[page]} →"
    assert at.page_link[-1].proto.page.endswith(nav.PAGES[following][2])


def test_the_food_page_opens_on_the_hook_food():
    at = render("food")
    assert not at.exception, at.exception
    assert at.selectbox[0].value == "Red onion"


@pytest.mark.parametrize(
    "name",
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
def test_an_old_food_link_opens_that_food_on_the_food_page(name):
    at = food(name)
    assert not at.exception, at.exception
    assert [h.value for h in at.header] == ["Check your food"]
    assert at.selectbox[0].value == name


def test_lines_under_the_headlines_say_how_to_read_each_chart():
    caught = [m.value for m in render("caught").markdown]
    assert any("lowest first" in v for v in caught)
    assert food_metrics(food("Red onion"))[2:] == ["Traders", "Stores"]


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
    """Each ECharts chart's option, in page order: the story's hook and ratchet,
    or who got caught's dots and growth."""
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


def test_the_middle_chart_is_one_bar_per_food_amber_where_the_store_grew_faster():
    middle = echarts(render("caught"))[1]
    foods = middle["yAxis"]["data"]
    assert len(foods) == 25 and foods[0] == "Red onion"
    (bars,) = middle["series"]
    colours = [d["itemStyle"]["color"] for d in bars["data"]]
    assert colours.count(views.AMBER) == 19
    labels = [d["label"]["formatter"] for d in bars["data"]]
    assert labels[0] == "+65 pts"  # store +48% against farm −17%
    assert labels[-1] == "−43 pts" and colours[-1] == views.MUTED
    # Every label sits right, so a grey bar's stays clear of the food names.
    assert {d["label"]["position"] for d in bars["data"]} == {"right"}


def test_every_chart_has_a_so_what_line():
    so_whats = [
        m.value
        for at in (render(), render("caught"), food("Red onion"))
        for m in at.markdown
        if ":material/lightbulb:" in m.value
    ]
    assert len(so_whats) == 7
    assert "farmers got only 30 centavos of every peso" in so_whats[0]
    assert "January's peak, they got 46" in so_whats[0]
    assert "farmers and fisherfolk are among the poorest" in so_whats[1]
    assert so_whats[2].endswith(
        "So of the ₱575 you pay, ₱274 is spent after the farm. Bought every week, "
        "that's about ₱1,187 a month."
    )
    assert "You pay ₱6 the farmer never saw" in so_whats[3]
    assert "for 15 of 21 foods, farmers get less than half" in so_whats[4]
    assert "the difference went to the middle" in so_whats[5]
    assert so_whats[6].startswith(":material/lightbulb: So red onion's farmer gets")


def test_the_public_record_is_on_the_page_rulings_first_each_sourced():
    at = render("caught")
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
    at = food("Kangkong")
    assert not at.exception, at.exception
    assert food_metrics(at)[2:] == ["The gap"]


def test_fish_shows_its_quarter_and_its_farmer_share():
    at = food("Bangus")
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
    charts = echarts(at) + echarts(render("caught"))
    dots = charts[2]
    assert len(dots["yAxis"][0]["data"]) == 21
    assert dots["yAxis"][0]["data"][0] == "Carrot"
    assert dots["yAxis"][1]["data"][0] == "23"
    for spec in charts:
        assert spec["animationDuration"] <= 1000
        assert "function" not in json.dumps(spec)


def test_every_series_eases_like_its_chart():
    # ECharts gives a line series its own linear easing, which overrides the
    # chart's: the hook's line crept at full speed to a dead stop (ticket 08).
    for spec in echarts(render()) + echarts(render("caught")):
        for series in spec["series"]:
            assert series["animationEasing"] == spec["animationEasing"], series


@pytest.mark.parametrize("page", PAGES)
def test_no_sentence_on_the_page_starts_with_a_numeral(page):
    at = render(page)
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
    at = food("Pork kasim")
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
    beef = food("Beef with bones")
    assert food_metrics(beef) == [
        "You pay, per kg beef",
        "Farm price, per kg live cattle",
    ]


@pytest.mark.parametrize("page", PAGES)
def test_headings_carry_no_link_so_the_page_always_opens_at_the_top(page):
    """A heading's link icon puts "#<heading>" in the address bar, and the
    browser then reopens the page scrolled to that heading."""
    at = render(page)
    headings = [*at.title, *at.header, *at.subheader]
    assert headings and all(h.proto.hide_anchor for h in headings)


def test_the_chain_names_each_step_and_cites_every_fact():
    """Section 2: four steps from farm to store, then what a fair cut pays for,
    each fact followed by a link to its source."""
    at = render()
    lines = [m.value for m in at.markdown]
    titles = [v for v in lines if v.startswith("**:material/") and v.endswith("**")]
    steps = titles[:4]
    assert [s.split("**")[1].split(" ", 1)[1] for s in steps] == [
        "Farmer",
        "Trader",
        "Wholesaler",
        "Store",
    ]
    arrows = [i for i, v in enumerate(lines) if v == views.CHAIN_ARROW]
    first = lines.index(steps[0])
    assert arrows == [first + 2, first + 5, first + 8]  # one between each step
    # Section 7's facts are on the caught page.
    page = " ".join(lines + [m.value for m in render("caught").markdown])
    for fact in context.facts():
        assert f"{fact.text} {views.cite(fact)}" in page
    assert views.cite(context.SPOILAGE) == (
        ":gray[([JESAM, UPLB, 2019](https://ovcre.uplb.edu.ph/journals-uplb/index.php"
        "/JESAM/article/download/89/69))]"
    )


def test_the_ratchet_is_a_still_example_of_three_moves_up_and_back():
    at = render()
    assert not any(b.key.startswith("ratchet") for b in at.button)  # no toy
    farm, store = echarts(at)[1]["series"]
    assert [s.get("color") for s in (farm, store)] == [None, None]
    assert [p[1] for p in farm["data"]] == [0, 10, 0, 10, 0, 10, 0]
    assert farm["endLabel"]["formatter"] == "back to start"
    assert store["endLabel"]["formatter"] == "+₱6"
    assert any(
        "the farm price is back where it started, but the store price is ₱6 "
        "higher. You pay ₱6 the farmer never saw." in m.value
        for m in at.markdown
    )


def test_the_reader_builds_their_own_basket_and_the_receipt_follows():
    at = render()
    basket = at.multiselect(key="basket")
    assert basket.value == [item for _, item, _ in data.BASKET]
    basket.set_value(["Rice, 1 kg", "Galunggong, 1 kg", "Carrot, 1 kg"]).run()
    assert not at.exception, at.exception
    receipt = at.table[0].value
    assert list(receipt.index) == [
        "Rice, 1 kg",
        "Galunggong, 1 kg",
        "Carrot, 1 kg",
        "**Total**",
    ]
    assert any(
        c.value.startswith(":material/receipt_long: Your basket") for c in at.caption
    )
    total = receipt.loc["**Total**"].str.strip("*₱").str.replace(",", "").astype(int)
    assert total.iloc[0] == total.iloc[1:].sum()
    at.multiselect(key="basket").set_value([]).run()
    assert not at.exception, at.exception
    assert not at.table
    assert "Pick a food to see its receipt." in [c.value for c in at.caption]


def test_the_story_links_to_the_short_version_and_opens_on_the_onion():
    at = render()
    assert at.page_link[0].value == "Short on time? Read the short version →"
    assert at.page_link[0].proto.page.endswith(nav.PAGES["short"][2])
    assert not any("New for" in m.value for m in at.markdown)
    assert at.caption[0].value.endswith("Updated with PSA's September 2026 release")


def test_the_short_version_says_the_whole_finding_in_bullets_with_no_charts():
    at = render("short")
    assert not at.exception, at.exception
    assert at.caption[1].value == "TL;DR"
    assert at.title[0].value == "The short version"
    assert not echarts(at) and not at.get("arrow_vega_lite_chart")
    (bullets,) = [m.value for m in at.markdown if m.value.startswith("- **")]
    lines = bullets.split("\n")
    assert [line.split("**")[1] for line in lines] == [
        "In March 2023, stores charged ₱155 a kilo more for onions than farmers got.",
        "Between the farmer and you stand traders, wholesalers and stores.",
        "Farmers get ₱46 of every ₱100 you pay.",
        "Traders take ₱5 more of every ₱100 than in 2018.",
        "When the farm price drops ₱10, you save only ₱8.",
        "It's not just onions: farmers get under half for 15 of 21 foods.",
        "It's not new: since 2018, store prices grew faster than farm prices for "
        "19 of 25 foods.",
        "Regulators have fined firms in the middle ₱1.76 billion so far.",
        "In September 2026, repolyo farmers' part rose to ₱49 of every ₱100.",
        context.SABOTAGE.text,
    ]
    # Each bullet: its bold finding, then a "so what" that starts with "So".
    assert all(line.split("** ", 1)[1].startswith("So ") for line in lines)
    assert [link.value for link in at.page_link] == [
        "Want the proof? Read the full story →",
        "Check your own food →",
        f"{views.NEXT['short']} →",
    ]


@pytest.mark.parametrize("page", list(views.CHAPTERS))
def test_each_section_carries_its_part_label_in_order(page):
    names = views.CHAPTERS[page]
    labels = [c.value for c in render(page).caption if c.value.startswith("Part ")]
    assert labels == [
        f"Part {i} of {len(names)} · {name}" for i, name in enumerate(names, 1)
    ]
