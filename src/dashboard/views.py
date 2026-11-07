"""The dashboard's 3 pages, one per mart group:

1. Overview: staple_prices_monthly + dish_costs_monthly. What moved in a year.
2. Compare places: staple_prices_monthly at province/region level. Where it costs more.
3. Look up a food: retail_prices_monthly + staple_seasonality. Any of PSA's foods.

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


# Page 1: Overview


def overview_page() -> None:
    staples = data.load(data.STAPLES)
    dishes = data.load(data.DISHES)
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

    left, right = st.columns([3, 2], gap="medium")
    with left, st.container(border=True, height="stretch"):
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
    with right, st.container(border=True, height="stretch"):
        st.subheader(
            "What dinner for 5 costs",
            help="Published recipes scaled to 5 servings, plus rice, priced at "
            f"this month's averages in {where}. A dish is left out where PSA has "
            "no price for one of its ingredients.",
        )
        meals = data.in_place(dishes, month, geo_code).dropna(subset=["dish_cost"])
        meals = meals.sort_values("dish_cost")
        table = pd.DataFrame(
            {
                "Dish": meals["dish"],
                "Cost": [f"₱{c:,.0f}" for c in meals["dish_cost"]],
                "vs a year ago": [
                    "—" if pd.isna(c) else data.arrow(c) for c in meals["change_year"]
                ],
            }
        ).reset_index(drop=True)
        st.dataframe(
            colored_changes(table, "vs a year ago"),
            hide_index=True,
            alt=f"Cost of each dinner for 5 in {where}",
        )

    footer(month, pd.Timestamp(staples["released_at"].max()))


# Page 2: Compare places


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


# Page 3: Look up a food


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
