"""The dashboard's 4 pages, one per mart group:

1. Farm to plate: farmer_share_monthly + dish_costs_monthly. The farmer's share of
   the retail peso, and what a dish costs in a day's minimum wage.
2. Overview: staple_prices_monthly. What moved in a year.
3. Compare places: staple_prices_monthly at province/region level. Where it costs more.
4. Look up a food: retail_prices_monthly + staple_seasonality. Any of PSA's foods.

Red means costs more and green costs less, always next to an arrow or a sign.
Everything else is neutral.
"""

import calendar
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from src.dashboard import data

# Mid-tones that read on both the light and dark theme backgrounds.
DEARER, CHEAPER, ACCENT = "#D9534A", "#3E9E66", "#5675BA"
MISSING = "rgba(138, 129, 120, 0.3)"
MUTED = "#8A8178"
MONTHS = list(calendar.month_abbr)[1:]
PHILIPPINES = data.PHILIPPINES


def peso(value: float) -> str:
    return f"₱{value:,.2f}"


def pct(change: float) -> str:
    """A signed delta: st.metric reads the sign for its arrow and colour."""
    return f"{change:+.1%}"


def change_color(field: str) -> Any:
    return (
        alt.when(alt.datum[field] > 0)
        .then(alt.value(DEARER))
        .otherwise(alt.value(CHEAPER))
    )


def month_badge(month: pd.Timestamp) -> None:
    """The data month, amber and marked late when it is over 2 months old."""
    now = pd.Timestamp(datetime.now(ZoneInfo("Asia/Manila")).date())
    late = month < now.to_period("M").to_timestamp() - pd.DateOffset(months=2)
    st.badge(
        f"{month:%B %Y} prices" + (" · late" if late else ""),
        icon=":material/warning:" if late else ":material/event:",
        color="orange" if late else "gray",
        help="PSA's latest monthly averages. PSA releases each month about 5 weeks "
        "after it ends.",
    )


def footer(month: pd.Timestamp, released: pd.Timestamp) -> None:
    st.divider()
    st.caption(
        f"Prices: PSA OpenSTAT, {month:%B %Y}, released {released:%d %b %Y}. "
        "Monthly averages, not one market's price tag. Province coverage is "
        "sparse, and pre-2024 figures for Negros Island Region and Sulu are PSA "
        "reconstructions."
    )


def colored_changes(frame: pd.DataFrame, column: str) -> Any:
    """Colour a column of data.arrow text red (↑) or green (↓)."""

    def tint(text: object) -> str:
        if str(text).startswith("↑"):
            return f"color: {DEARER}"
        return f"color: {CHEAPER}" if str(text).startswith("↓") else ""

    return frame.style.map(tint, subset=[column])


def month_axis() -> alt.X:
    return alt.X(
        "month:T", title=None, axis=alt.Axis(grid=False, format="%Y", tickCount="year")
    )


# Page 1: Farm to plate
# Lines and markers use the theme's categorical palette (range="category"), so
# they switch with light and dark at once: blue farm price, ink store price,
# amber policy. Explanations and caveats live in the (?) tooltips.

SHARE_HELP = (
    "Farm price ÷ store price, same food, place and month. Each food shows its "
    "latest month with both prices (hover a bar).\n\n"
    "- **Rice** is stored for months, so its share is approximate. Palay is "
    "converted to milled rice at 0.63, a figure from press and USDA coverage, "
    "not PSA.\n"
    "- A share can top ₱100 for a month or two: farm prices sometimes briefly "
    "exceed store prices (mostly sitaw, calamansi and tomato)."
)
WAGE_HELP = (
    "Published recipes scaled to 5 servings, plus rice, priced at the region's "
    "monthly averages, divided by its daily non-farm minimum wage (the top tier "
    "where a wage order has several). For the whole country: the median region.\n\n"
    "- Central Visayas, Northern Mindanao and BARMM use the rate of their "
    "highest-paid area (Metro Cebu, the Cagayan de Oro cluster, 3 cities), so "
    "they understate the cost elsewhere in those regions.\n"
    "- Negros Island Region has no wage order of its own yet."
)
ACTION = "Policy"


def share_chart(rows: pd.DataFrame, current: str) -> Any:
    """Each food's farmer pesos (blue) on a faint ₱100 track. Clicking a bar picks
    that food for the price chart (selection "pick"); the current food is solid,
    the rest faded."""
    scale = alt.Scale(domain=[0, max(100.0, float(rows["farmer"].max()))])
    base = alt.Chart(rows).encode(
        y=alt.Y("staple:N", sort=None, title=None, axis=alt.Axis(labelLimit=200)),
        tooltip=[
            alt.Tooltip("staple:N", title="Food"),
            alt.Tooltip("month:T", format="%B %Y", title="Month"),
            alt.Tooltip("farmer_share:Q", format=".1%", title="Farmer's share"),
            alt.Tooltip("farmgate_equivalent:Q", format=",.2f", title="Farm (₱)"),
            alt.Tooltip("retail_price:Q", format=",.2f", title="Store (₱)"),
        ],
    )
    track = base.mark_bar(color=MISSING, cornerRadiusEnd=3).encode(
        x=alt.datum(100, scale=scale)
    )
    farmer = (
        base.mark_bar(color=ACCENT, cornerRadiusEnd=3, cursor="pointer")
        .encode(
            x=alt.X(
                "farmer:Q",
                title=None,
                scale=scale,
                axis=alt.Axis(labelExpr="'₱' + datum.label", values=[0, 50, 100]),
            ),
            opacity=alt.when(alt.datum.staple == current)
            .then(alt.value(1.0))
            .otherwise(alt.value(0.4)),
        )
        .add_params(alt.selection_point(name="pick", fields=["staple"]))
    )
    # White inside the blue bar reads on both themes.
    text = (
        base.transform_calculate(pesos="'₱' + format(datum.farmer, '.0f')")
        .mark_text(align="right", dx=-5, color="white", fontWeight=600)
        .encode(x="farmer:Q", text="pesos:N")
    )
    return (track + farmer + text).properties(height=26 * len(rows))


def history_chart(history: pd.DataFrame, events: pd.DataFrame, unit: str) -> Any:
    names = [data.FARM, data.STORE] + ([ACTION] if len(events) else [])
    color = alt.Color(
        "line:N",
        scale=alt.Scale(domain=names, range="category"),
        legend=alt.Legend(title=None, orient="top"),
    )
    lines = (
        alt.Chart(history)
        .mark_line(strokeWidth=2.5)
        .encode(
            x=month_axis(),
            y=alt.Y(
                "price:Q",
                title=None,
                axis=alt.Axis(format=",.0f", labelExpr="'₱' + datum.label"),
            ),
            color=color,
            tooltip=[
                alt.Tooltip("line:N", title="Price"),
                alt.Tooltip("month:T", format="%B %Y", title="Month"),
                alt.Tooltip("price:Q", format=",.2f", title=f"₱ per {unit}"),
            ],
        )
    )
    marks = (
        alt.Chart(events)
        .transform_calculate(line=f"'{ACTION}'")
        .mark_rule(strokeDash=[4, 3], strokeWidth=1.5)
        .encode(
            x="start_date:T",
            color=color,
            tooltip=[
                alt.Tooltip("start_date:T", format="%d %b %Y", title="From"),
                alt.Tooltip("event:N", title=ACTION),
            ],
        )
    )
    return (lines + marks).properties(height=300)


def wage_chart(rows: pd.DataFrame) -> Any:
    """Each dish's share of a day's pay, with a dashed line at a full day's pay."""
    scale = alt.Scale(domain=[0, max(1.0, float(rows["dish_wage_share"].max()))])
    base = alt.Chart(rows).encode(
        y=alt.Y("dish:N", sort=None, title=None, axis=alt.Axis(labelLimit=200)),
        tooltip=[
            alt.Tooltip("dish:N", title="Dinner"),
            alt.Tooltip("dish_wage_share:Q", format=".1%", title="Of a day's pay"),
        ],
    )
    bars = base.mark_bar(color=ACCENT, cornerRadiusEnd=3).encode(
        x=alt.X(
            "dish_wage_share:Q",
            title=None,
            scale=scale,
            axis=alt.Axis(format="%", values=[0, 0.5, 1, 1.5, 2]),
        )
    )
    text = base.mark_text(align="right", dx=-5, color="white", fontWeight=600).encode(
        x="dish_wage_share:Q", text=alt.Text("dish_wage_share:Q", format=".1%")
    )
    # Ink (categorical colour 2), so the rule switches with light and dark.
    ink = alt.Scale(domain=["_", "day"], range="category")
    day = (
        alt.Chart(pd.DataFrame({"x": [1.0], "line": ["day"]}))
        .mark_rule(strokeDash=[4, 3], strokeWidth=1.5)
        .encode(
            x=alt.X("x:Q", scale=scale),
            color=alt.Color("line:N", scale=ink, legend=None),
        )
    )
    return (bars + text + day).properties(height=30 * len(rows))


def pick_food() -> None:
    """A click on the share chart picks that food in the price chart's selectbox."""
    picked = st.session_state["pick_food"]["selection"]["pick"]
    if picked:
        st.session_state["staple"] = picked[0]["staple"]


def pesos_change(change: float | None) -> str | None:
    # ASCII "-": st.metric reads the sign to pick the arrow, and a Unicode minus
    # shows as "↑ −₱7.3".
    return (
        None if change is None else f"{'+' if change >= 0 else '-'}₱{abs(change):.1f}"
    )


def farm_page() -> None:
    shares = data.load(data.SHARES)
    dishes = data.load(data.DISHES)
    names = data.regions(shares)
    wages = dishes.dropna(subset=["dish_wage_share"])
    wage_month = pd.Timestamp(wages["month"].max())

    with st.container(horizontal=True, vertical_alignment="center"):
        geo_code = str(
            st.selectbox(
                "Prices in",
                list(names),
                format_func=lambda code: names[code],
                key="region",
                bind="query-params",
                label_visibility="collapsed",
                width=300,
            )
        )
        month_badge(pd.Timestamp(shares["month"].max()))
    where = data.in_words(geo_code, names[geo_code])
    rows = data.farmer_shares(shares, geo_code)
    if rows.empty:
        st.info(f"PSA has no farm prices for {where}.")
        return

    # The takeaway is the title; the question is the small line under it.
    st.title(data.share_headline(rows))
    st.caption(f"How much of the store price reaches the farmer, in {where}")

    typical, typical_change = data.farmer_cut(shares, rows)
    rice, rice_change = data.farmer_cut(shares, rows, "Regular rice")
    dinner, dinner_change = data.dinner_cut(dishes, wage_month, geo_code)
    with st.container(horizontal=True):
        st.metric(
            "Farmer's cut, typical food",
            f"₱{typical:.0f} of ₱100",
            pesos_change(typical_change),
            delta_color="off",
            delta_description="vs a year ago",
            help=f"The median of {len(rows)} foods' farmer's share, each in its "
            "latest month. The change counts only foods priced both years.",
            border=True,
        )
        st.metric(
            "Farmer's cut, regular rice",
            "—" if rice is None else f"₱{rice:.0f} of ₱100",
            pesos_change(rice_change),
            delta_color="off",
            delta_description="vs a year ago",
            help="Palay converted to milled rice at 0.63; approximate, since rice "
            "is stored for months.",
            border=True,
        )
        st.metric(
            "Typical dinner for 5, share of a day's pay",
            "—" if dinner is None else f"{dinner:.1%}",
            None if dinner_change is None else f"{dinner_change * 100:+.1f} pts",
            delta_color="inverse",
            delta_description="vs a year ago",
            help="The median of 8 dinners' cost against the daily minimum wage, "
            f"{wage_month:%B %Y}"
            + (", in the median region." if geo_code == PHILIPPINES else "."),
            border=True,
        )

    staples = sorted(rows["staple"])
    out = data.load_exclusions()
    left_out = sorted(out.loc[out["geo_code"] == geo_code, "staple"])
    share_card, price_card = st.columns([5, 6], gap="medium")
    # The price card runs first: its selectbox decides which bar is highlighted.
    with price_card, st.container(border=True, height="stretch"):
        staple = str(
            st.selectbox(
                "Food",
                staples,
                index=staples.index("Regular rice") if "Regular rice" in staples else 0,
                key="staple",
                bind="query-params",
                label_visibility="collapsed",
                width=220,
            )
        )
        row = rows[rows["staple"] == staple].iloc[0]
        unit = "piece" if row["unit"] == "pc" else "kg"
        history = data.share_history(shares, staple, geo_code)
        first, last = history["month"].min(), history["month"].max()
        events = data.events_for(data.load_events(), staple, str(row["category"]))
        events = events[events["start_date"].between(first, last)]
        st.subheader(
            f"Farm and store price, per {unit}",
            help="Pick a food here or click its bar. Dashed lines: government "
            "policies on this food; hover one to read it."
            + (
                " Farm price here is palay ÷ 0.63, as milled rice."
                if row["category"] == "Rice"
                else ""
            ),
        )
        st.altair_chart(
            history_chart(history, events, unit).properties(
                height=max(260, 26 * len(rows) - 110)
            ),
            width="stretch",
            alt=f"{staple} farm and store price over time in {where}",
        )
        if len(events):
            with st.expander(f"Sources ({len(events)} policies)"):
                st.markdown(
                    "\n".join(
                        f"- {e.start_date:%d %b %Y}: [{e.event}]({e.source_url})"
                        for e in events.itertuples()
                    )
                )
    with share_card, st.container(border=True, height="stretch"):
        st.subheader(
            "Farmer's cut of every ₱100",
            help=SHARE_HELP
            + (
                f"\n- Left out here: {', '.join(left_out)}. Farm and store prices "
                "likely use different units (bundle vs kg)."
                if left_out
                else ""
            ),
        )
        st.altair_chart(
            share_chart(rows, staple),
            width="stretch",
            key="pick_food",
            on_select=pick_food,
            selection_mode="pick",
            alt=f"Farmer's share of the store price of each food in {where}",
        )

    with st.container(border=True):
        month = wage_month
        st.subheader("Dinner for 5, as a share of a day's minimum wage", help=WAGE_HELP)
        dinners = data.dish_wage_shares(dishes, month, geo_code)
        if dinners.empty:
            st.caption(f"{where} has no minimum wage order of its own yet.")
        else:
            st.caption(
                f"{month:%B %Y}"
                + (", median region" if geo_code == PHILIPPINES else "")
                + ". Dashed line: a full day's pay."
            )
            st.altair_chart(
                wage_chart(dinners),
                width="stretch",
                alt=f"Each dinner's cost as a share of a day's minimum wage in {where}",
            )

    st.divider()
    released = shares[["farmgate_released_at", "retail_released_at"]].max().max()
    st.caption(
        f"Farm and store prices: PSA OpenSTAT, latest release "
        f"{pd.Timestamp(released):%d %b %Y}. Minimum wages: NWPC regional wage orders."
    )


# Page 2: Overview


def overview_page() -> None:
    staples = data.load(data.STAPLES)
    month = data.latest_month(staples)
    year_ago = month - pd.DateOffset(years=1)
    names = data.regions(staples)

    with st.container(horizontal=True, vertical_alignment="center"):
        month_badge(month)
        geo_code = str(
            st.selectbox(
                "Prices in",
                list(names),
                format_func=lambda code: names[code],
                key="region",
                bind="query-params",
                label_visibility="collapsed",
                width=300,
            )
        )
    where = data.in_words(geo_code, names[geo_code])
    if data.in_place(staples, month, geo_code)["change_year"].isna().all():
        st.info(f"PSA has no year-on-year prices for {where} this month.")
        return
    summary = data.basket_summary(staples, month, geo_code)
    fell, rose = data.year_extremes(staples, month, 1, geo_code)
    st.title(data.headline(rose, fell) + " in a year")
    st.markdown(
        f"In {where}, {summary['dearer']} of {summary['staples']} everyday foods "
        f"cost more than in {year_ago:%B %Y}. The typical food costs "
        f"**{pct(summary['median'])}**."
    )

    with st.container(border=True):
        st.subheader("Typical food price vs a year earlier")
        st.caption(
            "Each month, the median of the everyday foods' yearly changes. Above "
            "zero: food got more expensive than the year before."
        )
        trend = data.typical_change_history(staples, geo_code)
        base = alt.Chart(trend).encode(
            x=month_axis(),
            y=alt.Y("typical:Q", title=None, axis=alt.Axis(format="+%")),
        )
        line = base.mark_line(color=MUTED, strokeWidth=2)
        dots = base.mark_circle(size=28).encode(
            color=change_color("typical"),
            tooltip=[
                alt.Tooltip("month:T", format="%B %Y", title="Month"),
                alt.Tooltip("typical:Q", format="+.1%", title="vs a year earlier"),
            ],
        )
        zero = alt.Chart().mark_rule(color=MUTED).encode(y=alt.datum(0))
        st.altair_chart(
            (line + dots + zero).properties(height=260),
            width="stretch",
            alt=f"Typical food price change vs a year earlier in {where}",
        )

    with st.container(border=True):
        st.subheader(f"Every food, {month:%b %Y} vs {year_ago:%b %Y}")
        st.caption("Right of the line: costs more than a year ago. Left: costs less.")
        rows = data.in_place(staples, month, geo_code).dropna(subset=["change_year"])
        rows = rows.assign(text=rows["change_year"].map(data.arrow))
        bars = alt.Chart(rows).encode(
            y=alt.Y("staple:N", sort="-x", title=None, axis=alt.Axis(labelLimit=180)),
            x=alt.X("change_year:Q", title=None, axis=alt.Axis(format="+%")),
        )
        chart = bars.mark_bar(cornerRadiusEnd=3).encode(
            color=change_color("change_year"),
            tooltip=[
                alt.Tooltip("staple:N", title="Food"),
                alt.Tooltip("text:N", title="Change"),
            ],
        )
        st.altair_chart(
            chart.properties(height=22 * len(rows)),
            width="stretch",
            alt=f"Yearly price change of each everyday food in {where}",
        )

    footer(month, pd.Timestamp(staples["released_at"].max()))


# Page 3: Compare places


def price_map(values: pd.DataFrame, geo_level: str, ncr: pd.DataFrame) -> Any:
    """A choropleth of each area's price against the national price."""
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
    source = {"values": features, "format": {"property": "features"}}
    return (
        alt.Chart(source)
        .mark_geoshape(stroke=MISSING, strokeWidth=0.5)
        .encode(
            color=color,
            tooltip=[
                alt.Tooltip("properties.label:N", title="Area"),
                alt.Tooltip("properties.value:Q", title="Price (₱)", format=",.2f"),
                alt.Tooltip(
                    "properties.vs_national:Q", title="vs national", format="+.1%"
                ),
            ],
        )
        .project("mercator")
        .properties(height=520)
    )


def area_table(rows: pd.DataFrame, alt_text: str) -> None:
    frame = pd.DataFrame(
        {
            "Area": rows["geolocation"].tolist(),
            "Price": [peso(float(v)) for v in rows["value"]],
            "vs national": rows["vs_national"].map(data.arrow).tolist(),
        }
    )
    st.dataframe(
        colored_changes(frame, "vs national"),
        hide_index=True,
        column_config={"Area": st.column_config.TextColumn(width="medium")},
        alt=alt_text,
    )


def places_page() -> None:
    staples = data.load(data.STAPLES)
    month = data.latest_month(staples)
    foods = sorted(staples["staple"].unique())

    with st.container(horizontal=True, vertical_alignment="bottom"):
        month_badge(month)
        food = str(
            st.selectbox(
                "Food",
                foods,
                index=foods.index("Regular rice") if "Regular rice" in foods else 0,
                key="food",
                bind="query-params",
                width=260,
            )
        )
        level = str(
            st.segmented_control(
                "Compare",
                ["Provinces", "Regions"],
                default="Provinces",
                required=True,
                key="level",
                bind="query-params",
            )
        )
    geo_level = "province" if level == "Provinces" else "region"
    values = data.area_values(staples, month, geo_level, food)
    if values.empty:
        st.info(f"PSA has no {level.lower()} prices for {food} this month.")
        return
    here = data.in_place(staples, month)
    national = here.loc[here["staple"] == food, "price"]
    unit = staples.loc[staples["staple"] == food, "unit"].iloc[0]
    low, high = values.iloc[0], values.iloc[-1]
    st.title(
        f"{food} costs most in {high['geolocation']}, least in {low['geolocation']}"
    )
    st.markdown(
        f"{peso(high['value'])} against {peso(low['value'])} "
        + ("per piece" if unit == "pc" else "per kg")
        + (
            f", national average {peso(float(national.iloc[0]))}."
            if len(national)
            else "."
        )
    )

    ncr = data.area_values(staples, month, "region", food)
    ncr = ncr[ncr["geo_code"] == data.NCR]
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.caption(
            "Red: costs more than the national average. Green: costs less. Grey: "
            f"no PSA price there ({len(values)} {level.lower()} priced)."
        )
        st.altair_chart(
            price_map(values, geo_level, ncr),
            width="stretch",
            alt=f"Map of {food} price by {geo_level}",
        )
    with right:
        with st.container(border=True):
            st.subheader("Cheapest", icon=":material/south:")
            area_table(values.head(5), f"Cheapest {level.lower()} for {food}")
        with st.container(border=True):
            st.subheader("Most expensive", icon=":material/north:")
            area_table(
                values.tail(5).iloc[::-1], f"Most expensive {level.lower()} for {food}"
            )

    footer(month, pd.Timestamp(staples["released_at"].max()))


# Page 4: Look up a food


def lookup_page() -> None:
    retail = data.load_mart()
    seasons = data.load(data.SEASONS)
    names = data.item_names(retail, data.load_basket())
    places = data.places(retail)

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
    in_where = "the Philippines" if place == PHILIPPINES else where
    st.title(f"{name} in {in_where}: {peso(found['price'])} {unit}")
    with st.container(horizontal=True):
        change = found["change_year"]
        st.metric(
            f"A year ago ({found['month'] - pd.DateOffset(years=1):%b %Y})",
            "—" if change is None else peso(found["year_ago"]),
            None if change is None else pct(change),
            delta_color="inverse",
            delta_description="since then",
            border=True,
        )
        if place != PHILIPPINES and found["vs_national"] is not None:
            st.metric(
                "National average",
                peso(found["national_price"]),
                pct(found["vs_national"]),
                delta_color="inverse",
                delta_description=f"{where} vs national",
                border=True,
            )

    lines = [found["series"].rename("price").reset_index().assign(line=where)]
    if place != PHILIPPINES:
        lines.append(
            found["national"].rename("price").reset_index().assign(line="Philippines")
        )
    with st.container(border=True):
        st.subheader("Price since 2018")
        st.caption(
            where + (" against the national average." if place != PHILIPPINES else ".")
        )
        chart = (
            alt.Chart(pd.concat(lines))
            .mark_line(strokeWidth=2)
            .encode(
                x=month_axis(),
                y=alt.Y(
                    "price:Q",
                    title=None,
                    scale=alt.Scale(zero=False),
                    axis=alt.Axis(format=",.0f", labelExpr="'₱' + datum.label"),
                ),
                color=alt.Color(
                    "line:N",
                    scale=alt.Scale(domain=[where, "Philippines"], range="category"),
                    legend=alt.Legend(title=None, orient="top"),
                ),
                tooltip=[
                    alt.Tooltip("line:N", title="Place"),
                    alt.Tooltip("month:T", format="%B %Y", title="Month"),
                    alt.Tooltip("price:Q", format=",.2f", title="Price (₱)"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, width="stretch", alt=f"{name} price over time")

    left, right = st.columns(2, gap="medium")
    season = seasons[seasons["staple"] == name]
    if not season.empty:
        with left, st.container(border=True, height="stretch"):
            best = season.loc[season["seasonal_index"].idxmin()]
            st.subheader(
                f"Usually cheapest in {calendar.month_name[int(best['calendar_month'])]}",
                help="Each calendar month's national price against its centred "
                f"13-month average, averaged over {int(best['years'])} years.",
            )
            st.caption("How far the price usually sits from normal, month by month.")
            bars = season.assign(
                month_name=season["calendar_month"].map(lambda m: MONTHS[m - 1]),
                text=season["seasonal_index"].map(data.arrow),
            )
            st.altair_chart(
                alt.Chart(bars)
                .mark_bar(cornerRadius=2)
                .encode(
                    x=alt.X(
                        "month_name:O",
                        sort=MONTHS,
                        title=None,
                        axis=alt.Axis(labelAngle=0),
                    ),
                    y=alt.Y("seasonal_index:Q", title=None, axis=alt.Axis(format="+%")),
                    color=change_color("seasonal_index"),
                    tooltip=[
                        alt.Tooltip("month_name:O", title="Month"),
                        alt.Tooltip("text:N", title="vs normal"),
                    ],
                )
                .properties(height=240),
                width="stretch",
                alt=f"Usual price swing of {name} by calendar month",
            )
    regions = data.region_prices(retail, commodity)
    if not regions.empty:
        with (
            right if not season.empty else left,
            st.container(border=True, height="stretch"),
        ):
            st.subheader("By region")
            st.caption(f"Latest price in each region. Line: {where}.")
            bars = (
                alt.Chart(regions)
                .mark_bar(color=MUTED, cornerRadiusEnd=2)
                .encode(
                    y=alt.Y(
                        "region:N",
                        sort="x",
                        title=None,
                        axis=alt.Axis(labelLimit=200, labelOverlap=False),
                    ),
                    x=alt.X("price:Q", title="Price (₱)"),
                    tooltip=[
                        alt.Tooltip("region:N", title="Region"),
                        alt.Tooltip("price:Q", format=",.2f", title="Price (₱)"),
                    ],
                )
            )
            here = (
                alt.Chart()
                .mark_rule(color=ACCENT, strokeWidth=2)
                .encode(x=alt.datum(found["price"]))
            )
            st.altair_chart(
                (bars + here).properties(height=24 * len(regions)),
                width="stretch",
                alt=f"{name} price by region",
            )

    st.caption(f"PSA item: {commodity}")
    footer(data.latest_month(retail), pd.Timestamp(retail["released_at"].max()))
