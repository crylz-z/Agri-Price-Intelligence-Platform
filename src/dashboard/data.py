"""The dashboard's only data access: the dbt mart on R2, read once per cache TTL.

The mart is one ~3 MB Parquet file, so the app fetches it whole (1 GET, Class B)
and filters in pandas. DuckDB over s3fs took 57 range reads and 76 s for the same
file on 2026-11-02; one cat_file took 2 s.
"""

import io

import pandas as pd
import pyarrow.parquet as pq
import streamlit as st
from dotenv import load_dotenv
from fsspec.implementations.local import LocalFileSystem

from src.core import storage

MART = "mart/retail_prices_monthly.parquet"
# PSA releases monthly; the cron checks daily, so a few hours of staleness is fine.
TTL_SECONDS = 6 * 60 * 60
GEO_LEVELS = ["national", "region", "province"]


def read_mart(root: str) -> pd.DataFrame:
    fs = storage.filesystem() if root.startswith("s3://") else LocalFileSystem()
    table = pq.read_table(io.BytesIO(fs.cat_file(f"{root}/{MART}")))
    df: pd.DataFrame = table.to_pandas(date_as_object=False)
    return df


@st.cache_data(ttl=TTL_SECONDS, show_spinner="Loading prices from R2...")
def load_mart() -> pd.DataFrame:
    load_dotenv()
    return read_mart(storage.root())


def geolocations(df: pd.DataFrame) -> list[str]:
    """National first, then regions, then provinces, each alphabetical."""
    geos = df[["geolocation", "geo_level"]].drop_duplicates()
    geos = geos.assign(order=geos["geo_level"].map(GEO_LEVELS.index))
    return list(geos.sort_values(["order", "geolocation"])["geolocation"])


def trend(df: pd.DataFrame, commodity: str, geos: list[str]) -> pd.DataFrame:
    rows = df[(df["commodity"] == commodity) & df["geolocation"].isin(geos)]
    return rows[["month", "geolocation", "price"]].sort_values("month")


def compare(
    df: pd.DataFrame, commodity: str, month: pd.Timestamp, geo_level: str
) -> pd.DataFrame:
    rows = df[
        (df["commodity"] == commodity)
        & (df["month"] == month)
        & (df["geo_level"] == geo_level)
    ]
    return rows[["geolocation", "price"]].sort_values("price", ascending=False)
