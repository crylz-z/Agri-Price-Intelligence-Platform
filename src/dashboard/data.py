"""The dashboard's only data access: the dbt marts on R2, read once per cache TTL.

Each mart is one small Parquet file, so the app fetches it whole (1 GET, Class B)
and filters in pandas. DuckDB over s3fs took 57 range reads and 76 s for the 3 MB
retail mart on 2026-11-02; one cat_file took 2 s.
"""

import io
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import streamlit as st
from dotenv import load_dotenv
from fsspec.implementations.local import LocalFileSystem

from src.core import storage

MART = "mart/retail_prices_monthly.parquet"
STAPLES = "mart/staple_prices_monthly.parquet"
DISHES = "mart/dish_costs_monthly.parquet"
SEASONS = "mart/staple_seasonality.parquet"
# The basket seed ships with the app, so it is read from the repo, not from R2.
BASKET = Path("dbt/seeds/staples.csv")
MAP = Path(__file__).parent / "assets" / "ph_provinces.geojson"
NCR = "130000000"
PHILIPPINES = "000000000"
# PSA releases monthly; the cron checks daily, so a few hours of staleness is fine.
TTL_SECONDS = 6 * 60 * 60
GEO_LEVELS = ["national", "region", "province"]
# A whole-file deadline: botocore's read_timeout counts per socket read, so a link
# that trickles bytes never trips it. Past this, fsspec raises FSTimeoutError; the
# error isn't cached, so a rerun tries again.
FETCH_TIMEOUT_SECONDS = 90


def read_parquet(root: str, path: str) -> pd.DataFrame:
    if root.startswith("s3://"):
        raw = storage.filesystem().cat_file(
            f"{root}/{path}", timeout=FETCH_TIMEOUT_SECONDS
        )
    else:
        raw = LocalFileSystem().cat_file(f"{root}/{path}")
    table = pq.read_table(io.BytesIO(raw))
    df: pd.DataFrame = table.to_pandas(date_as_object=False)
    return df


def read_mart(root: str) -> pd.DataFrame:
    return read_parquet(root, MART)


# Background refresh: after the TTL, visitors get the cached marts at once while a
# fresh copy loads; only the first visit after a restart waits for R2.
@st.cache_data(
    ttl=TTL_SECONDS,
    refresh_mode="background",
    show_spinner="Loading prices from R2...",
)
def load(path: str) -> pd.DataFrame:
    load_dotenv()
    return read_parquet(storage.root(), path)


def load_mart() -> pd.DataFrame:
    return load(MART)


@st.cache_data
def load_basket() -> pd.DataFrame:
    return pd.read_csv(BASKET)


@st.cache_data
def load_map() -> dict[str, Any]:
    geojson: dict[str, Any] = json.loads(MAP.read_text(encoding="utf-8"))
    return geojson


# Shared


def latest_month(df: pd.DataFrame) -> pd.Timestamp:
    return pd.Timestamp(df.loc[df["geo_level"] == "national", "month"].max())


def at(df: pd.DataFrame, month: pd.Timestamp, geo_level: str) -> pd.DataFrame:
    return df[(df["month"] == month) & (df["geo_level"] == geo_level)]


def in_place(
    df: pd.DataFrame, month: pd.Timestamp, geo_code: str = PHILIPPINES
) -> pd.DataFrame:
    """One month in one place (the whole country by default)."""
    return df[(df["month"] == month) & (df["geo_code"] == geo_code)]


def arrow(change: float) -> str:
    """0.041 -> '↑ 4.1%'; -0.2 -> '↓ 20.0%'. Colour never carries direction alone."""
    if round(change * 100, 1) == 0:
        return "– 0.0%"
    return f"{'↑' if change > 0 else '↓'} {abs(change):.1%}"


# Page 1: Overview


def regions(staples: pd.DataFrame) -> dict[str, str]:
    """geo code -> short name: the Philippines first, then regions A to Z.

    PSA's 'NCR - National Capital Region' becomes 'National Capital Region'.
    """
    rows = staples.loc[staples["geo_level"] == "region", ["geo_code", "geolocation"]]
    rows = rows.drop_duplicates("geo_code")
    names = {
        str(code): str(name).split(" - ", 1)[-1]
        for code, name in zip(rows["geo_code"], rows["geolocation"], strict=True)
    }
    return {PHILIPPINES: "Philippines"} | dict(
        sorted(names.items(), key=lambda kv: kv[1].lower())
    )


def in_words(geo_code: str, name: str) -> str:
    """A place as it reads after 'In': 'the Philippines', 'the Bicol Region',
    'the Zamboanga Peninsula', but 'Central Luzon' and 'CALABARZON'."""
    if geo_code == PHILIPPINES or "Region" in name or "Peninsula" in name:
        return f"the {name}"
    return name


def basket_summary(
    staples: pd.DataFrame, month: pd.Timestamp, geo_code: str = PHILIPPINES
) -> dict[str, Any]:
    """How a place's basket moved in a year: counts and the extremes."""
    rows = in_place(staples, month, geo_code).dropna(subset=["change_year"])
    rows = rows.sort_values("change_year")
    return {
        "staples": len(rows),
        "dearer": int((rows["change_year"] > 0).sum()),
        "cheaper": int((rows["change_year"] < 0).sum()),
        "median": float(rows["change_year"].median()),
        "top": rows.iloc[-1],
        "bottom": rows.iloc[0],
    }


def year_extremes(
    staples: pd.DataFrame, month: pd.Timestamp, n: int, geo_code: str = PHILIPPINES
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The n foods that fell most and the n that rose most in a year, biggest first.

    A food only counts as cheaper if it fell, and as pricier if it rose, so
    either list can be shorter than n.
    """
    rows = in_place(staples, month, geo_code).dropna(subset=["change_year"])
    fell = rows[rows["change_year"] < 0].nsmallest(n, "change_year")
    rose = rows[rows["change_year"] > 0].nlargest(n, "change_year")
    return fell, rose


def headline(rose: pd.DataFrame, fell: pd.DataFrame) -> str:
    """The biggest rise and fall: 'Repolyo up 34.9%, carrot down 28.5%'.

    Takes year_extremes' lists (biggest first); either may be empty. One decimal,
    so the headline agrees with the chart below it.
    """
    parts = [
        f"{rows.iloc[0]['staple']} {word} {abs(rows.iloc[0]['change_year']):.1%}"
        for rows, word in ((rose, "up"), (fell, "down"))
        if not rows.empty
    ]
    if not parts:
        return "Prices held steady"
    if len(parts) == 2:
        parts[1] = parts[1][0].lower() + parts[1][1:]
    return ", ".join(parts)


def typical_change_history(
    staples: pd.DataFrame, geo_code: str = PHILIPPINES
) -> pd.DataFrame:
    """Month by month, the median food's change vs a year earlier in one place.

    A median, so one food with a wild swing can't move the line.
    """
    rows = staples[staples["geo_code"] == geo_code].dropna(subset=["change_year"])
    out = rows.groupby("month", as_index=False).agg(typical=("change_year", "median"))
    return out.sort_values("month").reset_index(drop=True)


# Page 2: Compare places


def area_values(
    df: pd.DataFrame, month: pd.Timestamp, geo_level: str, staple: str
) -> pd.DataFrame:
    """One food's price in every area of a level, cheapest first.

    Region names lose PSA's numeral prefix: 'XII - SOCCSKSARGEN' -> 'SOCCSKSARGEN'.
    """
    rows = at(df, month, geo_level)
    rows = rows[(rows["staple"] == staple) & rows["price"].notna()]
    rows = rows.rename(columns={"price": "value"}).assign(
        geolocation=rows["geolocation"].str.split(" - ", n=1).str[-1]
    )
    cols = ["geo_code", "geolocation", "value", "vs_national"]
    return rows[cols].sort_values("value").reset_index(drop=True)


def map_features(
    geojson: dict[str, Any], values: pd.DataFrame, geo_level: str, ncr: pd.DataFrame
) -> dict[str, Any]:
    """Province shapes carrying the value of their province or their region.

    PSA prices NCR only as a region, so at province level NCR's districts take the
    region's value and say so in their label.
    """
    tables = {"own": values.set_index("geo_code"), "ncr": ncr.set_index("geo_code")}
    features = []
    for feature in geojson["features"]:
        props = feature["properties"]
        label, table = props["name"], tables["own"]
        code = props["geo_code"] if geo_level == "province" else props["region_code"]
        if geo_level == "province" and code is None and props["region_code"] == NCR:
            code, label, table = NCR, "NCR (region figure)", tables["ncr"]
        row = table.loc[code] if code in table.index else None
        if row is not None and geo_level == "region":
            label = row["geolocation"]
        features.append(
            {
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": {
                    "label": label,
                    "value": None if row is None else float(row["value"]),
                    "vs_national": None if row is None else float(row["vs_national"]),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


# Page 3: Look up a food


def item_names(retail: pd.DataFrame, staples: pd.DataFrame) -> dict[str, str]:
    """PSA commodity -> display name: the plain name for the basket, PSA's otherwise.

    Basket foods come first, then every other commodity alphabetically.
    """
    plain = dict(zip(staples["commodity"], staples["staple"], strict=True))
    others = sorted(set(retail["commodity"]) - set(plain))
    return {c: plain[c] for c in sorted(plain, key=lambda c: plain[c])} | {
        c: c.title() for c in others
    }


def places(retail: pd.DataFrame) -> dict[str, str]:
    """geo code -> name: national first, then regions, then provinces, alphabetical."""
    geos = retail[["geo_code", "geolocation", "geo_level"]].drop_duplicates("geo_code")
    geos = geos.assign(order=geos["geo_level"].map(GEO_LEVELS.index))
    geos = geos.sort_values(["order", "geolocation"])
    return dict(zip(geos["geo_code"], geos["geolocation"], strict=True))


def lookup(retail: pd.DataFrame, commodity: str, geo_code: str) -> dict[str, Any]:
    """One commodity in one place: its monthly series and the latest comparisons.

    The year-ago and national prices are matched by month, so gaps in a
    province's series never shift a comparison.
    """
    rows = retail[retail["commodity"] == commodity]
    series = rows[rows["geo_code"] == geo_code].set_index("month")["price"].sort_index()
    national = rows[rows["geo_level"] == "national"].set_index("month")["price"]
    if series.empty:
        return {"series": series, "national": national.sort_index()}
    month = series.index.max()
    price = float(series.iloc[-1])
    year_ago = series.get(month - pd.DateOffset(years=1))
    national_now = national.get(month)
    return {
        "series": series,
        "national": national.sort_index(),
        "month": month,
        "price": price,
        "year_ago": year_ago,
        "change_year": None if year_ago is None else price / year_ago - 1,
        "national_price": national_now,
        "vs_national": None if national_now is None else price / national_now - 1,
    }


def region_prices(retail: pd.DataFrame, commodity: str) -> pd.DataFrame:
    """One commodity's latest price in each region, cheapest first, with short names."""
    rows = retail[(retail["commodity"] == commodity) & retail["price"].notna()]
    rows = at(rows, latest_month(rows), "region")
    return (
        rows.assign(region=rows["geolocation"].str.split(" - ", n=1).str[-1])[
            ["region", "price"]
        ]
        .sort_values("price")
        .reset_index(drop=True)
    )
