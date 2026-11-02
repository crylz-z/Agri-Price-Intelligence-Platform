"""The dashboard's two pages: a price trend and an area comparison."""

import altair as alt
import pandas as pd
import streamlit as st

from src.dashboard import data

DEFAULT = "RICE, WELL-MILLED, 1 KG"


def pick_commodity(df: pd.DataFrame) -> str:
    left, right = st.columns(2)
    groups = sorted(df["commodity_group"].unique())
    group = left.selectbox("Commodity group", groups, index=groups.index("Cereals"))
    commodities = sorted(df.loc[df["commodity_group"] == group, "commodity"].unique())
    default = commodities.index(DEFAULT) if DEFAULT in commodities else 0
    return str(right.selectbox("Commodity", commodities, index=default))


def footer(df: pd.DataFrame) -> None:
    released = df["released_at"].max()
    st.caption(
        "Source: Philippine Statistics Authority, OpenSTAT retail prices of "
        f"agricultural commodities. Latest release {released:%Y-%m-%d}. "
        "Prices in pesos per the unit in the commodity name. "
        "Negros Island Region and Sulu values before 2024 are PSA back-casts to "
        "the 2024 boundaries. Many region and province months have no price."
    )


def trend_page() -> None:
    df = data.load_mart()
    st.title("Price trend")
    commodity = pick_commodity(df)
    geos = st.multiselect(
        "Geolocations", data.geolocations(df), default=["Philippines"]
    )
    rows = data.trend(df, commodity, geos)
    if rows.empty:
        st.info("No prices for this selection.")
    else:
        chart = (
            alt.Chart(rows)
            .mark_line(point=True)
            .encode(
                x=alt.X("month:T", title="Month"),
                y=alt.Y("price:Q", title="Price (PHP)"),
                color=alt.Color("geolocation:N", title="Geolocation"),
                tooltip=[
                    "month:T",
                    "geolocation:N",
                    alt.Tooltip("price:Q", format=".2f"),
                ],
            )
        )
        st.altair_chart(chart, width="stretch")
    footer(df)


def compare_page() -> None:
    df = data.load_mart()
    st.title("Compare areas")
    commodity = pick_commodity(df)
    left, right = st.columns(2)
    geo_level = left.radio("Level", ["region", "province"], horizontal=True)
    months = sorted(
        df.loc[df["commodity"] == commodity, "month"].unique(), reverse=True
    )
    month = right.selectbox("Month", months, format_func=lambda m: f"{m:%B %Y}")
    rows = data.compare(df, commodity, month, str(geo_level))
    if rows.empty:
        st.info("No prices for this selection.")
    else:
        chart = (
            alt.Chart(rows)
            .mark_bar()
            .encode(
                x=alt.X("price:Q", title="Price (PHP)"),
                y=alt.Y("geolocation:N", sort="-x", title=None),
                tooltip=["geolocation:N", alt.Tooltip("price:Q", format=".2f")],
            )
            .properties(height=max(200, 18 * len(rows)))
        )
        st.altair_chart(chart, width="stretch")
    footer(df)
