"""The dashboard's pages: four stories over the basket marts, plus a price lookup.

Design (dashboard-design skill, deviations per .claude/rules/dashboard.md): each
story page leads with a data-month badge and one headline sentence that answers
its question, then cards in one style that tell a shopper what to do, then the
main chart with a one-line "how to read it" caption. Red and green only mean
costs more and costs less, always next to an arrow or a sign; food-group hues
(FOOD_HUES) say what kind of food.
"""

import calendar
import html
import json
from collections.abc import Hashable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from src.dashboard import data

# Colours drawn in code are mid-tones that read on both themes' backgrounds
# (about 3:1 or better on #FAF7F2 and #171513), because Streamlit reports the
# viewer's theme one rerun late: a first visit in dark mode would otherwise get
# light-theme marks. Text, axes and plain lines take no colour here, so they
# follow the theme; diverging fills use the theme's own chartDivergingColors
# (range="diverging"), and two-line charts its chartCategoricalColors.
DEARER, CHEAPER, ACCENT = "#D9534A", "#3E9E66", "#5675BA"
MISSING = "rgba(138, 129, 120, 0.3)"  # warm grey, faint on either background
# Vega draws text and rules black unless told; this warm grey reads on both themes.
MUTED = "#8A8178"
# Food-group hues say what kind of food (chart labels); they avoid
# red and green (direction) and amber (data warnings).
FOOD_HUES = {
    "Rice": "#B8862B",
    "Meat": "#B05A8E",
    "Chicken and eggs": "#B87A48",
    "Fish": "#4A8CC4",
    "Vegetables": "#1F9A9A",
    "Beans": "#1F9A9A",
    "Spices": "#8A6CC4",
    "Fruit": "#7D8A99",
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]  # fmt: skip
PHILIPPINES = "000000000"
UNITS = {"kg": "per kg", "pc": "per piece"}
NOW_COLUMN = st.column_config.TextColumn(
    "Now", help="Average price per kg; eggs and coconuts per piece (/pc)."
)


def peso(value: float, unit: str | None = None) -> str:
    return f"₱{value:,.2f}" + (f"/{unit}" if unit else "")


def pct(change: float) -> str:
    """A signed delta: st.metric reads the sign for its arrow and colour."""
    return f"{change:+.1%}"


def badge(change: float) -> str:
    """A red or green badge with an arrow, as Markdown."""
    shown = round(change * 100, 1)
    color = "red" if shown > 0 else "green" if shown < 0 else "gray"
    return f":{color}-badge[{data.arrow(change)}]"


def change_color(field: str) -> Any:
    return (
        alt.when(alt.datum[field] > 0)
        .then(alt.value(DEARER))
        .otherwise(alt.value(CHEAPER))
    )


def shelf_price(price: float, unit: str) -> str:
    """A list price without '/kg', which clipped on phones; pieces keep '/pc'."""
    return peso(price, "pc" if unit == "pc" else None)


def ordinal(n: int) -> str:
    """1 -> '1st', 12 -> '12th', 23 -> '23rd'."""
    suffix = (
        "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def month_badge(month: pd.Timestamp, released: pd.Timestamp) -> None:
    """The data month, amber and marked late when it is over 2 months old."""
    # PSA publishes a month about 5 weeks after it ends; older than that is late.
    now = pd.Timestamp(datetime.now(ZoneInfo("Asia/Manila")).date())
    late = month < now.to_period("M").to_timestamp() - pd.DateOffset(months=2)
    st.badge(
        f"{month:%B %Y} prices" + (" · late" if late else ""),
        icon=":material/warning:" if late else ":material/event:",
        color="orange" if late else "gray",
        help=(
            f"PSA's latest monthly averages, published {released.day} "
            f"{released:%b %Y}. PSA releases each month about 5 weeks after "
            "it ends."
        ),
    )


def footer(month: pd.Timestamp, released: pd.Timestamp) -> None:
    st.divider()
    st.caption(
        f"Prices: PSA OpenSTAT, {month:%B %Y}, released {released:%d %b %Y}. "
        "PSA's monthly averages, not one market's price tag."
    )


def diverging_bars(
    rows: pd.DataFrame,
    label: str,
    field: str,
    title: str | None,
    group: str | None = None,
) -> Any:
    height = max(220, 26 * len(rows))
    # Every value label sits right of its bar's end or of the zero line, so it
    # never collides with the names on the left (which happened on phones).
    # Room past the longest rise for its label, in pixels (`padding` below): a
    # share of the axis clipped "↑ 34.9%" on phones and wasted space on desktops.
    reach = [1.1 * min(0.0, rows[field].min()), max(0.0, rows[field].max())]
    rows = rows.assign(
        text=rows[field].map(data.arrow), text_x=rows[field].clip(lower=0)
    )
    # Reserve room for the longest name up front: on a first visit Vega measures
    # labels before Inter has loaded and clipped their starts ("/ell-milled rice").
    room = min(180, 7 * int(rows[label].astype(str).str.len().max()) + 8)
    axis = alt.Axis(labelLimit=180, minExtent=room)
    if group:
        # Colour each name by its food group. No legend: on phones it squeezes
        # the plot until labels drop; the group is in the tooltip instead.
        hues = {str(r[label]): FOOD_HUES[str(r[group])] for _, r in rows.iterrows()}
        axis = alt.Axis(
            labelLimit=180,
            minExtent=room,
            labelColor=alt.expr(f"{json.dumps(hues)}[datum.value]"),
        )
    base = alt.Chart(rows).encode(
        y=alt.Y(
            f"{label}:N",
            sort=alt.EncodingSortField(field=field, order="descending"),
            title=None,
            axis=axis,
        ),
        x=alt.X(
            f"{field}:Q",
            title=title,
            axis=alt.Axis(format="+%", grid=False),
            scale=alt.Scale(domain=reach, padding=56, nice=False),
        ),
    )
    bars = base.mark_bar(cornerRadiusEnd=4, height=16).encode(
        color=change_color(field),
        tooltip=[f"{label}:N"]
        + ([alt.Tooltip(f"{group}:N", title="Group")] if group else [])
        + [alt.Tooltip("text:N", title="Change")],
    )
    text = base.mark_text(align="left", dx=5, fontSize=12, color=MUTED).encode(
        x="text_x:Q", text="text:N"
    )
    zero = alt.Chart().mark_rule(color=MUTED, strokeWidth=1).encode(x=alt.datum(0))
    return (bars + text + zero).properties(height=height)


# This month


def today_page() -> None:
    staples = data.load(data.STAPLES)
    dishes = data.load(data.DISHES)
    seasons = data.load(data.SEASONS)
    month = data.latest_month(staples)
    year_ago = month - pd.DateOffset(years=1)
    released = pd.Timestamp(staples["released_at"].max())
    last_month = month - pd.DateOffset(months=1)

    now = pd.Timestamp(datetime.now(ZoneInfo("Asia/Manila")).date())
    names = data.regions(staples)
    # "home" is the place a shopper last chose on either story page, so Where
    # you live and This month follow each other. Here it opens on home's region.
    home = str(st.session_state.get("home", PHILIPPINES))
    start = data.region_of(staples, home)
    with st.container(horizontal=True, vertical_alignment="center"):
        month_badge(month, released)
        geo_code = str(
            st.selectbox(
                "Prices in",
                list(names),
                index=list(names).index(start) if start in names else 0,
                format_func=lambda code: names[code],
                key="region",
                bind="query-params",
                label_visibility="collapsed",
                width=300,
            )
        )
    # A region chosen here becomes home, unless home is a province inside it.
    if geo_code not in (PHILIPPINES, start):
        st.session_state["home"] = geo_code
    where = data.in_words(geo_code, names[geo_code])
    if data.in_place(staples, month, geo_code)["change_year"].isna().all():
        st.info(f"PSA has no year-on-year prices for {where} this month.")
        return
    summary = data.basket_summary(staples, month, geo_code)

    # The headline names the year's biggest rise and fall: a shopper can act on
    # "repolyo up 34.9%" where "19 of 28 foods" only describes.
    fell, rose = data.year_extremes(staples, month, 4, geo_code)
    st.title(data.headline(rose, fell) + " in a year")
    st.markdown(
        f"In {where}, {summary['dearer']} of {summary['staples']} everyday foods "
        f"cost more than in {year_ago:%B %Y}."
    )

    # Punch first: what ₱100 of rice buys, and the cheapest dinner tonight.
    rice = data.peso_buys(staples, month, geo_code)
    meals = data.in_place(dishes, month, geo_code).dropna(subset=["dish_cost"])
    meals = meals.sort_values("dish_cost")
    cards = st.columns(2, gap="medium")
    if rice:
        kg = (
            100 / data.history(staples, "staple", "Regular rice", geo_code, 13)["price"]
        )
        with cards[0]:
            st.metric(
                "₱100 of regular rice buys",
                f"{rice['kg']:.2f} kg",
                delta=f"{rice['kg'] - rice['kg_year_ago']:+.2f} kg",
                delta_description="vs PY",
                # kg per ₱100 each month since PY; it takes the delta's red, which
                # here means rice got dearer, so the colour keeps its meaning.
                chart_data=kg.round(2).tolist(),
                chart_type="area",
                border=True,
                height="stretch",
                help=(
                    f"₱100 ÷ {peso(rice['price'], 'kg')} now. In "
                    f"{year_ago:%B %Y} it was {peso(rice['price_year_ago'], 'kg')}, "
                    f"so ₱100 bought {rice['kg_year_ago']:.2f} kg."
                ),
            )
    if not meals.empty:
        cheapest = meals.iloc[0]
        trend = data.history(dishes, "dish", cheapest["dish"], geo_code, 13)
        change = cheapest["change_year"]
        with cards[1] if rice else cards[0]:
            st.metric(
                f"Cheapest dinner for 5: {cheapest['dish']}",
                f"₱{cheapest['dish_cost']:,.0f}",
                delta=None if pd.isna(change) else pct(float(change)),
                delta_color="inverse",
                delta_description="vs PY",
                chart_data=trend["dish_cost"].round(0).tolist(),
                chart_type="area",
                border=True,
                height="stretch",
                help=(
                    "One meal, rice included, at this month's average prices in "
                    f"{where}. Every dish is under What dinner costs."
                ),
            )

    # The overview: every food's year change at once, names coloured by group.
    with st.container(border=True):
        st.subheader(
            f"All {summary['staples']} foods, vs PY",
            icon=":material/swap_vert:",
            help=(
                f"Average price in {where} now vs {year_ago:%B %Y} "
                "(PY = previous year, same month)."
            ),
        )
        st.caption(
            "Right of the line: costs more. Left: costs less. Colour = food group."
        )
        rows = data.in_place(staples, month, geo_code).dropna(subset=["change_year"])
        rows = rows[["staple", "category", "change_year"]].reset_index(drop=True)
        st.altair_chart(
            diverging_bars(rows, "staple", "change_year", None, group="category"),
            width="stretch",
            alt=f"Year-on-year price change of each everyday food in {where}",
        )
        # The bridge to Where you live: this chart is change over time; that
        # page is the same foods against the rest of the country.
        st.page_link(
            st.Page(places_page, title="Where you live", url_path="places"),
            label="Compare with other places",
            help=f"Where you live: {where} against the rest of the country.",
            icon=":material/arrow_forward:",
        )

    # The lists answer the shopper's question per aisle, so cheap vegetables
    # never crowd out a cheap pork cut: what to buy, what to go easy on, and
    # what to buy instead.
    aisle = st.segmented_control(
        "Aisle",
        list(data.AISLES),
        default=next(iter(data.AISLES)),
        required=True,
        key="aisle",
        label_visibility="collapsed",
    )
    aisle = str(aisle or next(iter(data.AISLES)))
    usual = data.seasonal_flags(seasons, now.month)
    cheaper, dearer = data.year_extremes(staples, month, 4, geo_code, aisle)
    pairs = data.swaps(staples, month, geo_code, n=len(staples))
    instead = dict(zip(pairs["staple"], pairs["swap"], strict=True))
    sides = (
        ("Buy now", ":material/savings:", cheaper, "fell", "costs less", None),
        (
            "Go easy on",
            ":material/trending_up:",
            dearer,
            "rose",
            "costs more",
            instead,
        ),
    )
    # Stacked full width: side by side, the trend and swap columns got cut off.
    for title, icon, rows, tip, empty, swap in sides:
        with st.container(border=True):
            st.subheader(
                title,
                icon=icon,
                help=(
                    f"The {aisle.lower()} foods whose average price in {where} "
                    f"{tip} most since {year_ago:%B %Y}. Trend: the last 13 months. "
                    f"Season: usually 5%+ cheaper or pricier in {now:%B}."
                ),
            )
            if rows.empty:
                st.caption(f"Nothing in {aisle.lower()} {empty} than PY.")
                continue
            shopping_list(rows, staples, geo_code, usual, swap)

    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True, height="stretch"):
        st.subheader("Moved most this month", icon=":material/bolt:")
        movers = data.movers(staples, month, "change_month", 5, geo_code)
        changes(
            pd.DataFrame(
                {
                    "Food": movers["staple"],
                    "Now": [
                        shelf_price(p, u)
                        for p, u in zip(movers["price"], movers["unit"], strict=True)
                    ],
                    f"vs {last_month:%b}": movers["change_month"].map(data.arrow),
                }
            ),
            alt=f"Foods whose price moved most since {last_month:%B}",
            Now=NOW_COLUMN,
        )
    with right, st.container(border=True, height="stretch"):
        st.subheader(
            "What dinner costs",
            icon=":material/restaurant:",
            help=(
                "One meal for 5: published recipes scaled to 5 servings, plus "
                f"0.5 kg rice, priced at this month's averages in {where}. A dish "
                "is left out where PSA has no price for one of its ingredients."
            ),
        )
        changes(
            pd.DataFrame(
                {
                    "Dish": meals["dish"],
                    "Cost": [f"₱{c:,.0f}" for c in meals["dish_cost"]],
                    "vs PY": [
                        "—" if pd.isna(c) else data.arrow(c)
                        for c in meals["change_year"]
                    ],
                }
            ),
            alt=f"Cost of each dinner for 5 in {where}",
        )
        st.page_link(
            st.Page(ulam_page, title="Ulam cost", url_path="ulam"),
            label="Recipes and amounts",
            icon=":material/arrow_forward:",
        )

    footer(month, released)


def changes(frame: pd.DataFrame, alt: str, **column_config: Any) -> None:
    """A full-width table whose arrowed changes ('↑ 4.1%') are red or green.

    Every column named 'vs ...' holds data.arrow text; the arrow carries the
    direction and the colour repeats it."""

    def tint(text: object) -> str:
        if str(text).startswith("↑"):
            return f"color: {DEARER}"
        return f"color: {CHEAPER}" if str(text).startswith("↓") else ""

    arrows: list[Hashable] = [c for c in frame.columns if str(c).startswith("vs ")]
    st.dataframe(
        frame.reset_index(drop=True).style.map(tint, subset=arrows),
        hide_index=True,
        column_config=column_config,
        alt=alt,
    )


def shopping_list(
    rows: pd.DataFrame,
    staples: pd.DataFrame,
    geo_code: str,
    usual: dict[str, float],
    instead: dict[str, str] | None,
) -> None:
    """Foods with their price, change vs PY, a 13-month trend that starts at the
    PY price, and a season flag; with `instead`, the cheaper food to try."""
    foods = [str(f) for f in rows["staple"]]
    season = {f: "Cheap" if usual[f] < 0 else "Pricey" for f in foods if f in usual}
    frame = pd.DataFrame(
        {
            "Food": foods,
            "Now": [
                shelf_price(float(p), str(u))
                for p, u in zip(rows["price"], rows["unit"], strict=True)
            ],
            "vs PY": rows["change_year"].map(data.arrow).tolist(),
            "Trend": [
                data.history(staples, "staple", f, geo_code, 13)["price"].tolist()
                for f in foods
            ],
        }
    )
    if season:  # only when a listed food has a season this month
        frame["Season"] = [season.get(f, "") for f in foods]
    config: dict[str, Any] = {
        "Now": NOW_COLUMN,
        # Rising lines are red and falling ones green, as everywhere else.
        "Trend": st.column_config.LineChartColumn("Trend", color="auto-inverse"),
    }
    if instead and any(f in instead for f in foods):
        frame["Try instead"] = [instead.get(f, "—") for f in foods]
        config["Try instead"] = st.column_config.TextColumn(
            "Try instead",
            help=(
                "The food in the same group that fell most since PY. Groups are "
                "broad: check it suits your dish."
            ),
        )
    changes(frame, alt="Foods, prices and their change since last year", **config)


# Where you live
#
# This month is change over time in one place; this page is your place against
# the rest of the country. It reads top to bottom as a story:
#   1. Hero: how much more (or less) food costs here, and whether that gap has
#      been growing (a gradient area of the typical gap, 3 years).
#   2. When to act: foods whose gap is far off its usual here, as cards with a
#      usual -> now track. A gap off its usual is a local squeeze or glut, so it
#      says "buy now" or "wait" where a plain gap only says "it's pricey here".
#   3. Every food on one quadrant chart: x = gap now, y = gap vs usual.
#   4. The map: the whole country, clickable.
# Styling for the hero, the cards and the tracks lives in app.py's CSS
# (classes .hero, .moves, .move, .track; keys st-key-hero-up / st-key-hero-down).

ALL_FOODS = "All everyday foods"


def rgba(hex_color: str, alpha: float) -> str:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alpha})"


def split_gradient(lo: float, hi: float, near: float, far: float) -> dict[str, Any]:
    """A vertical gradient over a mark spanning lo..hi (data units) that is green
    below zero and red above, `far` alpha at the outer edges and `near` at zero.

    Vega maps gradient offsets to the mark's bounding box, so zero's offset is
    computed from the data: offset 0 is the bottom (lo), 1 the top (hi).
    """
    span = hi - lo or 1.0
    zero = min(1.0, max(0.0, (0 - lo) / span))
    stops = []
    if zero > 0:
        stops += [
            {"color": rgba(CHEAPER, far), "offset": 0},
            {"color": rgba(CHEAPER, near), "offset": zero},
        ]
    if zero < 1:
        stops += [
            {"color": rgba(DEARER, near), "offset": zero},
            {"color": rgba(DEARER, far), "offset": 1},
        ]
    return {"gradient": "linear", "stops": stops, "x1": 0, "x2": 0, "y1": 1, "y2": 0}


def gap_area(history: pd.DataFrame) -> Any:
    """The typical gap month by month: a line over an area that is intense at the
    line and fades toward the national line (zero), red above and green below."""
    rows = history.assign(text=history["typical"].map(data.arrow))
    low, high = float(rows["typical"].min()), float(rows["typical"].max())
    reach = max(abs(low), abs(high), 0.05)
    # Keep some room on both sides of zero, so the national line never sits on
    # the chart's edge.
    domain = [min(low, -0.3 * reach) * 1.1, max(high, 0.3 * reach) * 1.15]
    x = alt.X(
        "month:T",
        title=None,
        axis=alt.Axis(format="%b %Y", grid=False, tickCount=6, labelColor=MUTED),
    )
    y = alt.Y(
        "typical:Q",
        title=None,
        scale=alt.Scale(domain=domain, nice=False),
        axis=alt.Axis(
            format="+%",
            tickCount=4,
            gridColor=rgba(MUTED, 0.18),
            gridDash=[2, 4],
            domain=False,
            ticks=False,
            labelColor=MUTED,
        ),
    )
    base = alt.Chart(rows).encode(x=x)
    area = base.mark_area(
        interpolate="monotone",
        color=split_gradient(min(low, 0), max(high, 0), 0.02, 0.5),
    ).encode(y=y, y2=alt.datum(0))
    line = base.mark_line(
        interpolate="monotone",
        strokeWidth=2.5,
        color=split_gradient(low, high, 1, 1),
    ).encode(y=y)
    zero = (
        alt.Chart()
        .mark_rule(color=MUTED, strokeDash=[4, 4], strokeWidth=1)
        .encode(y=alt.datum(0))
    )
    zero_label = (
        alt.Chart()
        .mark_text(align="left", dx=4, dy=-7, fontSize=11, color=MUTED)
        .encode(x=alt.value(0), y=alt.datum(0), text=alt.datum("national average"))
    )
    hover = base.mark_circle(size=260, opacity=0).encode(
        y=y,
        tooltip=[
            alt.Tooltip("month:T", title="Month", format="%B %Y"),
            alt.Tooltip("text:N", title="Typical food vs national"),
        ],
    )
    last = rows.tail(1)
    dot = (
        alt.Chart(last)
        .mark_circle(size=110, opacity=1, stroke="white", strokeWidth=2)
        .encode(x=x, y=y, color=change_color("typical"))
    )
    halo = (
        alt.Chart(last)
        .mark_circle(size=520, opacity=0.18)
        .encode(x=x, y=y, color=change_color("typical"))
    )
    # Transparent, so the hero card's gradient shows through the plot.
    return (zero + area + line + zero_label + halo + dot + hover).properties(
        height=240, background="transparent"
    )


def move_cards(rows: pd.DataFrame, reach: float) -> str:
    """HTML cards, one per food: its price here, then a track from cheaper
    (left) to pricier (right) than national, with a ring at its usual gap, a dot
    at today's and a bar between them."""

    def at(value: float) -> float:
        return round(50 + 50 * max(-1.0, min(1.0, value / reach)), 1)

    cards = []
    for row in rows.to_dict("records"):
        usual, now = float(row["usual"]), float(row["vs_national"])
        kind = "buy" if row["action"] == "buy" else "wait"
        left, right = sorted((at(usual), at(now)))
        unit = "pc" if row["unit"] == "pc" else "kg"
        cards.append(
            f'<div class="move {kind}">'
            f'<div class="move-head"><span class="move-name">'
            f"{html.escape(str(row['staple']))}</span>"
            f'<span class="move-price">₱{float(row["price"]):,.2f}'
            f"<small>/{unit}</small></span></div>"
            f'<div class="track"><span class="mid"></span>'
            f'<span class="bar" style="left:{left}%;width:{right - left}%"></span>'
            f'<span class="ring" style="left:{at(usual)}%"></span>'
            f'<span class="dot" style="left:{at(now)}%"></span></div>'
            f'<div class="move-foot"><span>usually {data.change_words(usual)}</span>'
            f"<b>now {data.change_words(now)}</b></div>"
            "</div>"
        )
    return f'<div class="moves">{"".join(cards)}</div>'


def act_chart(moves: pd.DataFrame, place: str, named: list[str]) -> Any:
    """Every food as a dot: across, its gap from national now; up, how far that
    gap sits above its usual here. The top half fades in red (wait), the bottom
    in green (good time), most intense far from 'usual'. Only the `named` foods
    (the cards above it) get a label; the rest have a tooltip."""
    xr = min(0.6, max(0.15, float(moves["vs_national"].abs().max()) * 1.1))
    yr = min(0.6, max(0.15, float(moves["shift"].abs().max()) * 1.15))
    rows = moves.assign(
        x=moves["vs_national"].clip(-xr, xr),
        y=moves["shift"].clip(-yr, yr),
        here=[
            peso(p, "pc" if u == "pc" else "kg")
            for p, u in zip(moves["price"], moves["unit"], strict=True)
        ],
        national=[
            peso(p, "pc" if u == "pc" else "kg")
            for p, u in zip(moves["national_price"], moves["unit"], strict=True)
        ],
        usually=moves["usual"].map(data.change_words),
        now=moves["vs_national"].map(data.change_words),
    )
    height = 420
    x = alt.X(
        "x:Q",
        title="← costs less than national · costs more →",
        scale=alt.Scale(domain=[-xr, xr], nice=False),
        axis=alt.Axis(
            format="+%",
            grid=False,
            tickCount=5,
            labelColor=MUTED,
            titleColor=MUTED,
            titleFontWeight=500,
            domain=False,
        ),
    )
    y = alt.Y(
        "y:Q",
        title=None,
        scale=alt.Scale(domain=[-yr, yr], nice=False),
        axis=None,
    )
    bands = pd.DataFrame(
        [
            {"x": -xr, "x2": xr, "y": 0.0, "y2": yr, "side": "wait"},
            {"x": -xr, "x2": xr, "y": -yr, "y2": 0.0, "side": "buy"},
        ]
    )
    band_x = alt.X("x:Q", scale=alt.Scale(domain=[-xr, xr], nice=False), title=None)
    band_y = alt.Y("y:Q", scale=alt.Scale(domain=[-yr, yr], nice=False), axis=None)
    top = (
        alt.Chart(bands[bands["side"] == "wait"])
        .mark_rect(color=split_gradient(0, 1, 0, 0.16))
        .encode(x=band_x, x2="x2", y=band_y, y2="y2")
    )
    bottom = (
        alt.Chart(bands[bands["side"] == "buy"])
        .mark_rect(color=split_gradient(-1, 0, 0, 0.16))
        .encode(x=band_x, x2="x2", y=band_y, y2="y2")
    )
    zero_y = alt.Y(datum=0, scale=alt.Scale(domain=[-yr, yr], nice=False), axis=None)
    rule_y = alt.Chart().mark_rule(color=MUTED, strokeWidth=1).encode(y=zero_y)
    rule_x = (
        alt.Chart()
        .mark_rule(color=MUTED, strokeWidth=1, strokeDash=[3, 4])
        .encode(x=alt.datum(0))
    )
    corner = {"fontSize": 12, "fontWeight": 700, "align": "left"}
    wait_label = (
        alt.Chart()
        .mark_text(color=DEARER, baseline="top", dy=8, **corner)
        .encode(
            x=alt.value(8),
            y=alt.Y(datum=yr, scale=alt.Scale(domain=[-yr, yr], nice=False), axis=None),
            text=alt.datum("↑ WAIT · higher than usual here"),
        )
    )
    buy_label = (
        alt.Chart()
        .mark_text(color=CHEAPER, baseline="bottom", dy=-8, **corner)
        .encode(
            x=alt.value(8),
            y=alt.Y(
                datum=-yr, scale=alt.Scale(domain=[-yr, yr], nice=False), axis=None
            ),
            text=alt.datum("↓ GOOD TIME · lower than usual here"),
        )
    )
    usual_label = (
        alt.Chart()
        .mark_text(align="right", dx=-6, dy=-7, fontSize=11, color=MUTED)
        .encode(x=alt.value("width"), y=zero_y, text=alt.datum("usual"))
    )
    color = (
        alt.when(alt.datum.action == "buy")
        .then(alt.value(CHEAPER))
        .when(alt.datum.action == "wait")
        .then(alt.value(DEARER))
        .otherwise(alt.value(MUTED))
    )
    tooltip = [
        alt.Tooltip("staple:N", title="Food"),
        alt.Tooltip("here:N", title=place),
        alt.Tooltip("national:N", title="National"),
        alt.Tooltip("usually:N", title="Usually here"),
        alt.Tooltip("now:N", title="Now here"),
    ]
    points = alt.Chart(rows)
    halos = (
        points.transform_filter("datum.action !== 'usual'")
        .mark_circle(size=420, opacity=0.16)
        .encode(x=x, y=y, color=color)
    )
    dots = points.mark_circle(opacity=0.95).encode(
        x=x,
        y=y,
        color=color,
        size=alt.condition("datum.action === 'usual'", alt.value(60), alt.value(130)),
        tooltip=tooltip,
    )
    # Each name goes right of its dot, left near the right edge, and above or
    # below when two named dots sit close (Vega-Lite has no label placement).
    labelled = rows[rows["staple"].isin(named)].sort_values("x")
    spot: dict[Hashable, str] = {}
    for i, row in labelled.iterrows():
        spot[i] = "left" if row["x"] > 0.6 * xr else "right"
        for j, other in labelled.loc[list(spot)[:-1]].iterrows():
            if (
                abs(row["y"] - other["y"]) < 0.08 * yr
                and abs(row["x"] - other["x"]) < 0.3 * xr
            ):
                spot[j], spot[i] = "above", "below"
    # A name on the right would run into a named dot just right of it.
    for i, row in labelled.iterrows():
        crowded = labelled[
            (labelled["x"] > row["x"])
            & (labelled["x"] - row["x"] < 0.3 * xr)
            & ((labelled["y"] - row["y"]).abs() < 0.12 * yr)
        ]
        if spot[i] == "right" and not crowded.empty:
            spot[i] = "left"
    labelled = labelled.assign(spot=pd.Series(spot, dtype=str))
    text = {"fontSize": 12, "fontWeight": 600}
    offsets = {
        "right": {"align": "left", "dx": 10, "baseline": "middle"},
        "left": {"align": "right", "dx": -10, "baseline": "middle"},
        "above": {"align": "center", "dy": -12, "baseline": "bottom"},
        "below": {"align": "center", "dy": 12, "baseline": "top"},
    }
    names = [
        alt.Chart(labelled[labelled["spot"] == side])
        .mark_text(**text, **style)
        .encode(x=x, y=y, text="staple:N", color=color)
        for side, style in offsets.items()
        if (labelled["spot"] == side).any()
    ]
    return alt.layer(
        top,
        bottom,
        rule_y,
        rule_x,
        usual_label,
        wait_label,
        buy_label,
        halos,
        dots,
        *names,
    ).properties(height=height)  # fmt: skip


def price_map(
    values: pd.DataFrame,
    geo_level: str,
    ncr: pd.DataFrame,
    unit_label: str,
    *,
    gap_only: bool = False,
    outline: str | None = None,
    clickable: bool = False,
) -> Any:
    """A choropleth of each area against the national price.

    gap_only: the values are typical gaps, so the tooltip shows no price.
    outline: a province or region code to ring in the accent colour.
    clickable: a click selects the shape's geo code (selection "area", field "geo").
    """
    features = data.map_features(data.load_map(), values, geo_level, ncr)
    reach = max(0.1, min(0.4, float(values["vs_national"].abs().max() or 0.1)))
    color = (
        alt.when("datum.properties.value === null")
        .then(alt.value(MISSING))
        .otherwise(
            alt.Color(
                "properties.vs_national:Q",
                title="vs national",
                scale=alt.Scale(domain=[-reach, reach], range="diverging", clamp=True),
                legend=alt.Legend(
                    format="+%", orient="bottom-left", gradientLength=160
                ),
            )
        )
    )
    tooltip = [alt.Tooltip("properties.label:N", title="Area")]
    if not gap_only:
        tooltip.append(
            alt.Tooltip("properties.value:Q", title=unit_label, format=",.2f")
        )
    tooltip.append(
        alt.Tooltip(
            "properties.vs_national:Q",
            title="Typical food vs national" if gap_only else "vs national",
            format="+.1%",
        )
    )
    source = {"values": features, "format": {"property": "features"}}
    shapes = (
        alt.Chart(source)
        .mark_geoshape(stroke=MISSING, strokeWidth=0.5)
        .encode(color=color, tooltip=tooltip)
    )
    if clickable:
        # NCR's districts have no province code; a click on one picks NCR.
        shapes = shapes.transform_calculate(
            geo="datum.properties.geo_code || datum.properties.region_code"
        ).add_params(alt.selection_point(name="area", fields=["geo"], on="click"))
    layers = [shapes]
    if outline:
        layers.append(
            alt.Chart(source)
            .transform_filter(
                f"datum.properties.geo_code === '{outline}'"
                f" || datum.properties.region_code === '{outline}'"
            )
            .mark_geoshape(filled=False, stroke=ACCENT, strokeWidth=2.5)
        )
    return alt.layer(*layers).project("mercator").properties(height=560)


def ranked(rows: pd.DataFrame, unit: str) -> None:
    for _, row in rows.iterrows():
        st.markdown(
            f"{row['geolocation']} · **{peso(row['value'], unit)}** "
            f"{badge(row['vs_national'])}"
        )


def area_list(rows: pd.DataFrame, gap_only: bool, unit: str, alt: str) -> None:
    """Areas with their price (unless gap_only) and their gap from national."""
    frame = pd.DataFrame({"Area": rows["geolocation"].tolist()})
    if not gap_only:
        frame["Price"] = [shelf_price(float(v), unit) for v in rows["value"]]
    frame["vs national"] = rows["vs_national"].map(data.arrow).tolist()
    changes(frame, alt=alt)


def places_page() -> None:
    staples = data.load(data.STAPLES)
    month = data.latest_month(staples)
    released = pd.Timestamp(staples["released_at"].max())
    names = data.place_names(staples)
    regions = data.regions(staples)

    # Opens on "home", the place last chosen on either story page.
    home = str(st.session_state.get("home", data.NCR))
    start = home if home in names else data.NCR

    def follow_map() -> None:
        """A click on the map makes that area the place."""
        chosen = st.session_state["map"]["selection"].get("area") or []
        code = chosen[0].get("geo") if chosen else None
        if code in names:
            st.session_state["place"] = code

    with st.container(horizontal=True, vertical_alignment="center"):
        month_badge(month, released)
        place = str(
            st.selectbox(
                "Your place",
                list(names),
                index=list(names).index(start),
                format_func=lambda code: names[code],
                key="place",
                bind="query-params",
                label_visibility="collapsed",
                width=300,
                help="Type to search. Or click a province on the map.",
            )
        )
    st.session_state["home"] = place
    level = "region" if place in regions else "province"
    short = regions.get(place, names[place])
    where = data.in_words(place, short) if level == "region" else short

    basket = data.place_basket(staples, month, place)
    if basket.empty:
        st.info(f"PSA priced none of the everyday foods in {where} this month.")
        footer(month, released)
        return
    st.title(data.place_headline(basket, where))

    # 1. Hero: the typical gap, where it ranks, and its last 3 years.
    gaps = data.typical_gaps(staples, month, level)
    mine = gaps[gaps["geo_code"] == place].iloc[0]
    gap = float(mine["vs_national"])
    peers = "regions" if level == "region" else "provinces and cities"
    history = data.gap_history(staples, place, 37)
    year_ago = history[history["month"] == month - pd.DateOffset(years=1)]
    more = int((basket["vs_national"] > 0).sum())
    chips = [
        data.rank_words(int(mine["rank"]), len(gaps), peers),
        f"{more} of {len(basket)} foods cost more here",
    ]
    if not year_ago.empty:
        chips.append(f"a year ago: {data.arrow(float(year_ago['typical'].iloc[0]))}")
    side = "up" if round(gap, 3) > 0 else "down"
    with st.container(key=f"hero-{side}"):
        st.html(
            '<div class="hero">'
            f'<div class="hero-kicker">Typical food in {html.escape(short)}</div>'
            f'<div class="hero-row"><span class="hero-num {side}">{data.arrow(gap)}</span>'
            f'<span class="hero-sub">{"more" if side == "up" else "less"} than the '
            "national average</span></div>"
            f'<div class="chips">{"".join(f"<span>{html.escape(c)}</span>" for c in chips)}</div>'
            "</div>"
        )
        st.altair_chart(
            gap_area(history),
            width="stretch",
            alt=f"Typical food price in {short} against national, last 3 years",
        )
        st.caption(
            "Typical food: the middle of the foods' gaps from the national price, "
            "so one odd price can't move it.",
            help=(
                f"The median gap between {where}'s price and the national average "
                f"across the {int(mine['foods'])} everyday foods PSA priced here."
            ),
        )

    # 2. When to act: foods whose gap is far off its usual here.
    moves = data.place_moves(staples, month, place)
    buy = moves[moves["action"] == "buy"].head(4)
    wait = moves[moves["action"] == "wait"].iloc[::-1].head(4)
    shown = pd.concat([buy, wait])
    reach = max(
        0.1,
        float(shown[["usual", "vs_national"]].abs().max().max()) * 1.1
        if not shown.empty
        else 0.1,
    )
    columns = st.columns(2, gap="medium")
    sides = (
        (columns[0], "Good time to buy here", ":material/shopping_basket:", buy,
         "cheaper than usual"),
        (columns[1], "Wait if you can", ":material/hourglass_top:", wait,
         "pricier than usual"),
    )  # fmt: skip
    for column, title, icon, rows, empty in sides:
        with column:
            st.subheader(
                title,
                icon=icon,
                help=(
                    f"Foods whose gap from the national price in {where} is 5 "
                    "points or more off its usual (the median of the last 3 "
                    "years). Ring: usual. Dot: now. Left of centre: costs less "
                    "than national."
                ),
            )
            if rows.empty:
                st.caption(f"Nothing is {empty} here this month.")
            else:
                st.html(move_cards(rows, reach))

    # 3. Every food at once.
    if not moves.empty:
        with st.container(border=True):
            st.subheader(
                f"Every food in {short}",
                icon=":material/scatter_plot:",
                help=(
                    "Across: this month's gap from the national price. Up: how far "
                    "that gap sits above its usual here (median of the last 3 "
                    "years). Coloured dots are 5 points or more off usual; the "
                    "named ones are the cards above."
                ),
            )
            st.altair_chart(
                act_chart(moves, short, shown["staple"].tolist()),
                width="stretch",
                alt=f"Each food in {short}: gap from national now and against usual",
            )

    # 4. The map: the whole country at a glance, for all foods or one.
    foods = sorted(staples["staple"].unique())
    with st.container(border=True):
        st.subheader(
            "Across the country",
            icon=":material/map:",
            help=(
                "Each province against the national average price. All everyday "
                "foods: the typical food's gap. PSA prices NCR only as a region, "
                "so its cities share the region's colour."
            ),
        )
        item = str(
            st.selectbox(
                "Food on the map",
                [ALL_FOODS, *foods],
                key="food",
                bind="query-params",
                label_visibility="collapsed",
                width=300,
            )
        )
        gap_only = item == ALL_FOODS
        if gap_only:
            values = data.typical_gaps(staples, month, "province")
            ncr = data.typical_gaps(staples, month, "region")
            unit = ""
        else:
            values = data.area_values(staples, month, "province", "staple", item)
            ncr = data.area_values(staples, month, "region", "staple", item)
            unit = str(staples.loc[staples["staple"] == item, "unit"].iloc[0])
        ncr = ncr[ncr["geo_code"] == data.NCR]
        # A city has no shape of its own: ring the province it sits in (PSGC:
        # the first 4 digits of a city's code are its province's).
        outline = place if level == "region" else place[:4] + "00000"
        st.caption(
            "Red: costs more than the national price. Green: costs less. Grey: no "
            f"PSA price. Ringed: {short}. Click a province to make it your place."
        )
        if values.empty:
            st.info(f"PSA has no province prices for {item} this month.")
        else:
            left, right = st.columns([3, 2], gap="large")
            with left:
                st.altair_chart(
                    price_map(
                        values,
                        "province",
                        ncr,
                        f"Peso/{unit}",
                        gap_only=gap_only,
                        outline=outline,
                        clickable=True,
                    ),
                    width="stretch",
                    key="map",
                    on_select=follow_map,
                    selection_mode="area",
                    alt=f"Map of {item.lower()} prices by province against national",
                )
            with right:
                what = "the typical food" if gap_only else item.lower()
                st.markdown(f"**Cheapest** for {what}")
                area_list(values.head(5), gap_only, unit, f"Cheapest areas for {what}")
                st.markdown(f"**Most expensive** for {what}")
                area_list(
                    values.tail(5).iloc[::-1],
                    gap_only,
                    unit,
                    f"Most expensive areas for {what}",
                )

    # Back to This month, which opens on this place's region (via "home").
    region = regions[data.region_of(staples, place)]
    st.page_link(
        st.Page(today_page, title="This month", url_path="today"),
        label="What changed here this year",
        help=f"This month for {region}: every food against a year ago.",
        icon=":material/arrow_forward:",
    )
    footer(month, released)


# Ulam cost


def amount(quantity: float, unit: str) -> str:
    if unit == "pc":
        return f"{quantity:g} pcs"
    return f"{quantity * 1000:,.0f} g" if quantity < 1 else f"{quantity:g} kg"


def ulam_page() -> None:
    staples = data.load(data.STAPLES)
    dishes = data.load(data.DISHES)
    recipes = data.load_recipes()
    month = data.latest_month(dishes)
    year_ago = month - pd.DateOffset(years=1)

    st.caption(f":material/restaurant: Ulam cost · {month:%B %Y}")
    names = sorted(dishes["dish"].unique())
    dish = st.pills(
        "Dish",
        names,
        default="Sinigang na baboy",
        required=True,
        key="dish",
        bind="query-params",
    )
    dish = str(dish)
    national = data.history(dishes, "dish", dish, PHILIPPINES)
    now = national.iloc[-1]
    peak = national.loc[national["dish_cost"].idxmax()]
    st.title(f"{dish} for a family of 5 costs ₱{now['dish_cost']:,.0f}")

    with st.container(horizontal=True):
        st.metric(
            "Today",
            f"₱{now['dish_cost']:,.0f}",
            pct(float(now["change_year"])),
            delta_color="inverse",
            delta_description=f"vs {year_ago:%b %Y}",
            border=True,
            help="One meal, rice included, at this month's national average prices.",
        )
        st.metric(
            "A year ago",
            f"₱{now['dish_cost_year_ago']:,.0f}",
            border=True,
        )
        st.metric(
            "Most expensive month so far",
            f"₱{peak['dish_cost']:,.0f}",
            delta=f"{peak['month']:%B %Y}",
            delta_color="off",
            delta_arrow="off",
            border=True,
        )

    left, right = st.columns([1, 1], gap="large")
    with left, st.container(border=True):
        st.subheader("Cost of the same meal since 2018", icon=":material/show_chart:")
        st.caption(
            "The recipe never changes, so the line only moves when food prices do. "
            "Blue dot: today."
        )
        base = alt.Chart(national).encode(
            x=alt.X(
                "month:T",
                title=None,
                axis=alt.Axis(grid=False, format="%Y", tickCount="year"),
            ),
            y=alt.Y(
                "dish_cost:Q",
                title=None,
                scale=alt.Scale(zero=False),
                axis=alt.Axis(
                    format=",.0f", labelExpr="'₱' + datum.label", tickCount=5
                ),
            ),
        )
        line = base.mark_line(strokeWidth=2).encode(
            tooltip=[
                alt.Tooltip("month:T", format="%B %Y", title="Month"),
                alt.Tooltip("dish_cost:Q", format=",.0f", title="Cost (₱)"),
            ]
        )
        dot = base.transform_filter(
            alt.datum.month == alt.expr.toDate(now["month"].isoformat())
        ).mark_point(filled=True, size=90, color=ACCENT)
        st.altair_chart(
            (line + dot).properties(height=320),
            width="stretch",
            alt=f"{dish} cost over time",
        )
    with right, st.container(border=True):
        st.subheader("What's in the pot", icon=":material/soup_kitchen:")
        lines = data.dish_breakdown(staples, recipes, month, PHILIPPINES, dish)
        total = float(lines["line_cost"].sum())
        st.caption(
            "Amounts scaled from a published recipe for 5. Oil, salt, soy sauce and "
            "vinegar aren't counted."
        )
        st.dataframe(
            lines.assign(
                amount=[
                    amount(q, u)
                    for q, u in zip(lines["quantity"], lines["unit"], strict=True)
                ],
                share=100 * lines["line_cost"] / total,
            )[["staple", "amount", "line_cost", "share", "source"]],
            hide_index=True,
            column_config={
                "staple": "Ingredient",
                "amount": "Amount",
                "line_cost": st.column_config.NumberColumn("Cost", format="₱%.0f"),
                "share": st.column_config.ProgressColumn(
                    "Share",
                    format="%.0f%%",
                    min_value=0,
                    max_value=100,
                    color="gray",
                ),
                "source": st.column_config.LinkColumn(
                    "Recipe", display_text="source", help="Blank: our estimate"
                ),
            },
            alt=f"Ingredients and costs of {dish}",
        )

    with st.container(border=True):
        st.subheader("Every dish, now vs a year ago", icon=":material/compare_arrows:")
        st.caption("Sorted cheapest first. Red arrow: costs more than a year ago.")
        table = data.at(dishes, month, "national").sort_values("dish_cost")
        table = table.assign(change=table["change_year"].map(data.arrow))
        styled = table[["dish", "dish_cost", "dish_cost_year_ago", "change"]].style.map(
            lambda text: "color: " + (DEARER if text.startswith("↑") else CHEAPER),
            subset=["change"],
        )
        st.dataframe(
            styled,
            hide_index=True,
            column_config={
                "dish": "Dish",
                "dish_cost": st.column_config.NumberColumn("Now", format="₱%.0f"),
                "dish_cost_year_ago": st.column_config.NumberColumn(
                    f"{year_ago:%b %Y}", format="₱%.0f"
                ),
                "change": st.column_config.TextColumn("Change", width="small"),
            },
            alt="Dish costs now and a year ago",
        )

    st.header("Where it costs most", icon=":material/map:")
    values = data.area_values(dishes, month, "province", "dish", dish)
    ncr = data.area_values(dishes, month, "region", "dish", dish)
    ncr = ncr[ncr["geo_code"] == data.NCR]
    priced = len(values)
    provinces = data.at(dishes, month, "province")["geo_code"].nunique()
    if values.empty:
        st.info("No province has a price for every ingredient this month.")
    else:
        left, right = st.columns([3, 2], gap="large")
        with left:
            st.caption(
                f"Red: costs more than the national cost. Green: costs less. Grey: PSA "
                f"didn't price every ingredient there ({priced} of {provinces} "
                "areas have a full price)."
            )
            st.altair_chart(
                price_map(values, "province", ncr, "Pesos"),
                width="stretch",
                alt=f"Map of {dish} cost by province",
            )
        with right:
            with st.container(border=True):
                st.subheader("Cheapest", icon=":material/south:")
                ranked(values.head(5), "")
            with st.container(border=True):
                st.subheader("Most expensive", icon=":material/north:")
                ranked(values.tail(5).iloc[::-1], "")
    footer(month, staples["released_at"].max())


# When to buy


def seasons_page() -> None:
    staples = data.load(data.STAPLES)
    seasons = data.load(data.SEASONS)
    month = data.latest_month(staples)
    coming = datetime.now(ZoneInfo("Asia/Manila")).month
    this_month = calendar.month_name[coming]

    st.caption(":material/calendar_month: When to buy")
    rows = data.season_extremes(seasons, coming)
    cheap, dear = rows.iloc[0], rows.iloc[-1]
    st.title(
        f"In {this_month}, {dear['staple']} usually costs more than normal and "
        f"{cheap['staple']} less"
    )
    with st.container(horizontal=True):
        st.metric(
            f"{dear['staple']} in {this_month}",
            "Costs more than normal",
            pct(float(dear["seasonal_index"])),
            delta_color="inverse",
            border=True,
            help="How far its price usually sits from the rest of the year, "
            f"averaged over {int(dear['years'])} years.",
        )
        st.metric(
            f"{cheap['staple']} in {this_month}",
            "Costs less than normal",
            pct(float(cheap["seasonal_index"])),
            delta_color="inverse",
            border=True,
            help="How far its price usually sits from the rest of the year, "
            f"averaged over {int(cheap['years'])} years.",
        )

    swing = seasons.groupby("staple")["seasonal_index"].agg(lambda s: s.max() - s.min())
    order = list(swing.sort_values(ascending=False).index)
    grid = seasons.assign(
        month_name=seasons["calendar_month"].map(lambda m: MONTHS[m - 1]),
        text=seasons["seasonal_index"].map(data.arrow),
    )
    heat = (
        alt.Chart(grid)
        .mark_rect(cornerRadius=3)
        .encode(
            x=alt.X(
                "month_name:O",
                sort=MONTHS,
                title=None,
                axis=alt.Axis(orient="top", labelAngle=0),
                # Gaps between cells, in place of a background-coloured stroke.
                scale=alt.Scale(paddingInner=0.06),
            ),
            y=alt.Y(
                "staple:N",
                sort=order,
                title=None,
                scale=alt.Scale(paddingInner=0.12),
            ),
            color=alt.Color(
                "seasonal_index:Q",
                title="vs normal",
                scale=alt.Scale(domain=[-0.2, 0.2], range="diverging", clamp=True),
                legend=alt.Legend(format="+%", orient="bottom", gradientLength=240),
            ),
            tooltip=[
                alt.Tooltip("staple:N", title="Food"),
                alt.Tooltip("month_name:O", title="Month"),
                alt.Tooltip("text:N", title="vs normal"),
                alt.Tooltip("years:Q", title="Years averaged"),
            ],
        )
    )
    now = (
        alt.Chart(pd.DataFrame({"month_name": [MONTHS[coming - 1]]}))
        .mark_rect(fill=None, stroke=ACCENT, strokeWidth=2)
        .encode(x=alt.X("month_name:O", sort=MONTHS))
    )
    with st.container(border=True):
        st.subheader("The palengke calendar", icon=":material/grid_on:")
        st.caption(
            "Green: usually cheaper than normal that month, a good time to buy. Red: "
            f"usually costs more. Foods that swing most are on top. Outlined: "
            f"{this_month}."
        )
        st.altair_chart(
            (heat + now).properties(height=30 * len(order)),
            width="stretch",
            alt="Usual price swing of each food by calendar month",
        )
    footer(month, staples["released_at"].max())


# Look up a price


def lookup_page() -> None:
    retail = data.load_mart()
    seasons = data.load(data.SEASONS)
    basket = data.load_basket()
    names = data.item_names(retail, basket)
    places = data.places(retail)

    st.caption(":material/search: Look up a price")
    with st.container(horizontal=True, vertical_alignment="bottom"):
        commodity = str(
            st.selectbox(
                "Food",
                list(names),
                index=list(names).index("RICE, REGULAR-MILLED, 1 KG"),
                format_func=lambda c: names[c],
                key="item",
                bind="query-params",
                help="The 28 everyday foods first, then every other item PSA prices.",
            )
        )
        place = str(
            st.selectbox(
                "Place",
                list(places),
                format_func=lambda c: places[c],
                key="where",
                bind="query-params",
            )
        )
    name, where = names[commodity], places[place]
    found = data.lookup(retail, commodity, place)
    if "price" not in found:
        st.info(f"PSA has no price for {name} in {where}.")
        return

    unit = "per piece" if "1 PC" in commodity else "per kg"
    st.title(
        f"{name} in {'the Philippines' if place == PHILIPPINES else where}: {peso(found['price'])} {unit}"
    )
    with st.container(horizontal=True):
        change = found["change_year"]
        st.metric(
            f"A year ago, {found['month'] - pd.DateOffset(years=1):%b %Y}",
            "—" if change is None else peso(found["year_ago"]),
            None if change is None else pct(change),
            delta_color="inverse",
            delta_description="since then",
            border=True,
        )
        if place != PHILIPPINES and found["vs_national"] is not None:
            st.metric(
                "National price",
                peso(found["national_price"]),
                pct(found["vs_national"]),
                delta_color="inverse",
                delta_description=f"{where} vs national",
                border=True,
            )
        season = seasons[seasons["staple"] == name]
        if not season.empty:
            best = season.loc[season["seasonal_index"].idxmin()]
            st.metric(
                "Usually cheapest in",
                calendar.month_name[int(best["calendar_month"])],
                pct(float(best["seasonal_index"])),
                delta_color="inverse",
                delta_description="vs normal",
                border=True,
            )

    series = found["series"].rename("price").reset_index().assign(line=where)
    lines = [series]
    if place != PHILIPPINES:
        lines.append(
            found["national"].rename("price").reset_index().assign(line="Philippines")
        )
    with st.container(border=True):
        st.subheader("Price since 2018", icon=":material/show_chart:")
        st.caption(
            "Dark line: "
            + where
            + (". Grey: the national average." if place != PHILIPPINES else ".")
        )
        chart = (
            alt.Chart(pd.concat(lines))
            .mark_line(strokeWidth=2)
            .encode(
                x=alt.X(
                    "month:T",
                    title=None,
                    axis=alt.Axis(grid=False, format="%Y", tickCount="year"),
                ),
                y=alt.Y(
                    "price:Q",
                    title=None,
                    scale=alt.Scale(zero=False),
                    axis=alt.Axis(
                        format=",.0f", labelExpr="'₱' + datum.label", tickCount=5
                    ),
                ),
                color=alt.Color(
                    "line:N",
                    scale=alt.Scale(
                        domain=[where, "Philippines"],
                        range="category",
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("line:N", title="Place"),
                    alt.Tooltip("month:T", format="%B %Y", title="Month"),
                    alt.Tooltip("price:Q", format=",.2f", title="Price (₱)"),
                ],
            )
            .properties(height=340)
        )
        st.altair_chart(chart, width="stretch", alt=f"{name} price over time")
    st.caption(f"PSA item: {commodity}")
    footer(data.latest_month(retail), retail["released_at"].max())
