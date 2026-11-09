"""The dashboard's only data access: the dbt marts on R2, read once per cache TTL.

Each mart is one small Parquet file, so the app fetches it whole (1 GET, Class B)
and filters in pandas. DuckDB over s3fs took 57 range reads and 76 s for the 3 MB
retail mart on 2026-11-02; one cat_file took 2 s.
"""

import io
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import streamlit as st
from dotenv import load_dotenv
from fsspec.implementations.local import LocalFileSystem

from src.core import storage

SHARES = "mart/farmer_share_monthly.parquet"
VERDICTS = "mart/food_verdicts.parquet"
CHANGES = "mart/price_changes_yearly.parquet"
CHANGE_ONLY = "mart/change_only_monthly.parquet"
# The suspects seed is hand-kept and ships with the app, so it is read from the
# repo: editing the CSV on main is its only upkeep.
SUSPECTS = Path("dbt/seeds/suspects.csv")
PHILIPPINES = "000000000"
# PSA releases monthly; the cron checks daily, so a few hours of staleness is fine.
TTL_SECONDS = 6 * 60 * 60
# A whole-file deadline: botocore's read_timeout counts per socket read, so a link
# that trickles bytes never trips it. Past this, fsspec raises FSTimeoutError; the
# error isn't cached, so a rerun tries again.
FETCH_TIMEOUT_SECONDS = 90
# Short, so the price chart's legend fits a phone; its y axis says pesos.
FARM, WHOLESALE, STORE = "Farm", "Wholesale", "Store"
# The three parts of every ₱100 a shopper pays, in supply-chain order.
FARMER, TRADERS, STORES = "Farmer", "Traders", "Stores"


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


@st.cache_data
def load_suspects() -> pd.DataFrame:
    return pd.read_csv(SUSPECTS, parse_dates=["source_date", "checked"])


def farmer_shares(shares: pd.DataFrame, geo_code: str = PHILIPPINES) -> pd.DataFrame:
    """Each staple's latest farmer's share in one place, smallest share first.

    Staples differ in their latest month. `farmer` is the farmer's pesos of every
    ₱100 and `rest` what is left of the ₱100 (0 when farmgate tops retail). The
    wholesale price splits `rest` into `traders` (farm to wholesale) and `stores`
    (wholesale to shelf), each clipped to the rest; both are NaN without one.
    """
    rows = shares[shares["is_latest"] & (shares["geo_code"] == geo_code)]
    rows = rows.dropna(subset=["farmer_share"]).sort_values("farmer_share")
    farmer = rows["farmer_share"] * 100
    rest = (100 - farmer).clip(lower=0)
    traders = (rows["trader_cut"] / rows["retail_price"] * 100).clip(0, rest)
    return rows.assign(
        farmer=farmer, rest=rest, traders=traders, stores=rest - traders
    ).reset_index(drop=True)


def typical_peso(rows: pd.DataFrame) -> tuple[dict[str, float], int]:
    """The typical peso: the average farmer's, traders' and stores' centavos over
    the foods with all three parts, and how many foods that is. An average, not a
    median, so the parts add up to 100 (each part's median need not)."""
    split = rows.dropna(subset=["traders"])
    means = split[["farmer", "traders", "stores"]].mean()
    parts = dict(zip((FARMER, TRADERS, STORES), means.astype(float)))
    return parts, len(split)


def whole_centavos(parts: dict[str, float]) -> dict[str, int]:
    """Round each part to whole centavos so they still add up to the rounded
    total (largest remainder), e.g. 33.4 + 33.3 + 33.3 -> 34 + 33 + 33."""
    floors = {name: int(value // 1) for name, value in parts.items()}
    short = round(sum(parts.values())) - sum(floors.values())
    by_remainder = sorted(parts, key=lambda name: parts[name] % 1, reverse=True)
    for name in by_remainder[:short]:
        floors[name] += 1
    return floors


def parts_then_now(verdicts: pd.DataFrame) -> dict[str, float]:
    """The typical food's (median) traders' and stores' pesos of every ₱100, in
    2018 and over the last 12 months. Foods without a wholesale price drop out."""
    columns = [
        f"{who}_part_{when}" for who in ("trader", "store") for when in ("then", "now")
    ]
    medians = verdicts[columns].median()
    return {column: float(medians[column]) for column in columns}


def ratchet(up: float, down: float, swings: int = 3) -> pd.DataFrame:
    """An example for the reader, not data: the farm price rises ₱10 and falls ₱10
    `swings` times while the store price follows by `up` and `down` pesos. Long,
    one row per step and line; `price` is pesos from where each line started."""
    farm, store, rows = 0.0, 0.0, [(0, 0.0, 0.0)]
    for _ in range(swings):
        farm, store = farm + 10, store + round(up)
        rows.append((len(rows), farm, store))
        farm, store = farm - 10, store - round(down)
        rows.append((len(rows), farm, store))
    steps = pd.DataFrame(rows, columns=["step", FARM, STORE])
    return steps.melt("step", var_name="line", value_name="price")


def national_series(shares: pd.DataFrame, staple: str) -> pd.DataFrame:
    """One staple's national farm, wholesale and store price by month, long, for a
    line chart. Months without a wholesale price have only the other two.

    Farm price is the retail-equivalent (palay as milled rice), so all lines are
    pesos for the same unit.
    """
    rows = shares[(shares["staple"] == staple) & (shares["geo_code"] == PHILIPPINES)]
    rows = rows.dropna(subset=["farmgate_equivalent", "retail_price"])
    rows = rows.sort_values("month")
    lines = (
        ("farmgate_equivalent", FARM),
        ("wholesale_price", WHOLESALE),
        ("retail_price", STORE),
    )
    return pd.concat(
        [
            pd.DataFrame({"month": rows["month"], "price": rows[column], "line": line})
            for column, line in lines
        ],
        ignore_index=True,
    ).dropna(subset=["price"])


def since_2018(monthly: pd.DataFrame, staple: str) -> pd.DataFrame:
    """One change-only food's farm and store price by month as a change from its
    2018 average, long, for a line chart. Percent, since its farm and store prices
    are for different products (a live hog, a kilo of kasim)."""
    rows = monthly[monthly["staple"] == staple].sort_values("month")
    base = rows[rows["month"].dt.year == 2018]
    return pd.concat(
        [
            pd.DataFrame(
                {
                    "month": rows["month"],
                    "change": rows[column] / base[column].mean() - 1,
                    "line": line,
                }
            )
            for column, line in (("farm", FARM), ("store", STORE))
        ],
        ignore_index=True,
    )


def farm_fell(changes: pd.DataFrame) -> pd.DataFrame:
    """The foods whose farm price fell over the past year, biggest split first:
    the store's change minus the farm's, so "farm down, store up" leads."""
    rows = changes[changes["farm_change"] < 0]
    split = rows["store_change"] - rows["farm_change"]
    return (
        rows.assign(split=split)
        .sort_values("split", ascending=False)
        .reset_index(drop=True)
    )


def growth_vs_prices(verdicts: pd.DataFrame) -> pd.DataFrame:
    """Each staple's growth in the middle's cut since 2018, biggest first, with
    whether it beat inflation (the mart's verdict)."""
    rows = verdicts.sort_values("middle_change", ascending=False)
    return rows[["staple", "middle_change", "verdict"]].reset_index(drop=True)


def grew_faster(growth: pd.DataFrame, change: float) -> int:
    """How many foods' gap grew faster than `change` (e.g. diesel), compared as
    the whole percents the chart labels show, so a tie on screen isn't counted."""
    shown = (growth["middle_change"] * 100).round()
    return int((shown > round(change * 100)).sum())


# Fewer months than this in either direction and a food's up/down pair is noise.
MIN_MOVE_MONTHS = 6


def up_and_down(verdicts: pd.DataFrame) -> pd.DataFrame:
    """Each staple's store peso move per ₱10 of farm move, when the farm price rose
    (`up`) and when it fell (`down`), smallest `down` first. Only staples with
    MIN_MOVE_MONTHS in each direction."""
    rows = verdicts[
        (verdicts["up_months"] >= MIN_MOVE_MONTHS)
        & (verdicts["down_months"] >= MIN_MOVE_MONTHS)
    ]
    rows = rows.assign(
        up=rows["up_pass_through"] * 10, down=rows["down_pass_through"] * 10
    ).sort_values("down")
    return rows[["staple", "up", "down", "up_months", "down_months"]].reset_index(
        drop=True
    )


def claims_for(suspects: pd.DataFrame, staple: str, category: str) -> pd.DataFrame:
    """The public record about one staple, or about its whole category ('Rice'),
    newest first."""
    rows = suspects[suspects["staple"].isin([staple, category])]
    return rows.sort_values("source_date", ascending=False).reset_index(drop=True)
