"""The dashboard's only data access: the dbt marts on R2, read once per cache TTL.

Each mart is one small Parquet file, so the app fetches it whole (1 GET, Class B)
and filters in pandas. DuckDB over s3fs took 57 range reads and 76 s for the 3 MB
retail mart on 2026-11-02; one cat_file took 2 s.
"""

import io
from collections.abc import Sequence
from pathlib import Path
from typing import Any

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
GROWTH = "mart/growth_since_2018.parquet"
SEASONAL = "mart/seasonal_baseline.parquet"
# Under this swing (5%: rice 2%, egg 4%, tomato 36%) a food has no season worth
# judging the month against, so the page says so instead.
MIN_SEASON_SWING = 0.05
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
# The page's hook: the 2023 onion crisis, national. The months are a fixed choice
# (Dec 2022's farm price sits above the store's, and Aug to Nov 2022 have none);
# every number shown comes from the mart.
HOOK_FOOD = "Red onion"
HOOK_START, HOOK_END = pd.Timestamp("2023-01-01"), pd.Timestamp("2023-06-01")


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


def ratchet(up: float, down: float, moves: Sequence[int]) -> pd.DataFrame:
    """An example for the reader, not data: each move (+1 or −1) takes the farm price ₱10 up or down, and the store price follows by
    `up` or `down` pesos. Long, one row per step and line; `price` is pesos from
    where each line started."""
    farm, store, rows = 0.0, 0.0, [(0, 0.0, 0.0)]
    for move in moves:
        farm += 10 * move
        store += round(up) if move > 0 else -round(down)
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


def hook(shares: pd.DataFrame) -> pd.DataFrame:
    """The hook's months, HOOK_START to HOOK_END: HOOK_FOOD's national farm,
    wholesale and store price, wide, one row per month, plus the farmer's
    centavos of every peso (`farmer`)."""
    rows = shares[
        (shares["staple"] == HOOK_FOOD)
        & (shares["geo_code"] == PHILIPPINES)
        & shares["month"].between(HOOK_START, HOOK_END)
    ].sort_values("month")
    return pd.DataFrame(
        {
            "month": rows["month"],
            FARM: rows["farmgate_equivalent"],
            WHOLESALE: rows["wholesale_price"],
            STORE: rows["retail_price"],
            "farmer": rows["farmer_share"] * 100,
        }
    ).reset_index(drop=True)


def outran(growth: pd.DataFrame) -> pd.DataFrame:
    """Each food's farm and store growth since 2018, the store's biggest lead
    first. `outran` is True when the store price grew faster than the farm price,
    compared as the whole percents the chart labels show."""
    rows = growth.assign(
        lead=growth["store_change"] - growth["farm_change"],
        outran=(growth["store_change"] * 100).round()
        > (growth["farm_change"] * 100).round(),
    )
    return rows.sort_values("lead", ascending=False).reset_index(drop=True)


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


# The receipt's example basket (ADR 24): our pick, labelled an example on screen.
# Each food has a farm, wholesale and store price; meat can't be split in pesos.
# (staple, line on the receipt, how many of the mart's unit)
BASKET = (
    ("Regular rice", "Rice, 1 kg", 1),
    ("Galunggong", "Galunggong, 1 kg", 1),
    ("Tomato", "Tomato, 1 kg", 1),
    ("Red onion", "Red onion, ½ kg", 0.5),
    ("Egg", "Eggs, 12", 12),
)


def basket_choices(shares: pd.DataFrame) -> tuple[tuple[str, str, float], ...]:
    """Every food the reader can put in their basket: the example basket's
    first, as BASKET words them, then each other food with a national farm,
    wholesale and store price in its latest month, one of its unit ("Ginger,
    1 kg"), A to Z."""
    latest = shares[shares["is_latest"] & (shares["geo_code"] == PHILIPPINES)]
    latest = latest.dropna(subset=["wholesale_price"])
    picked = {staple for staple, _, _ in BASKET}
    others = sorted(
        (str(row.staple), f"{row.staple}, 1 {'piece' if row.unit == 'pc' else 'kg'}", 1)
        for row in latest.itertuples()
        if row.staple not in picked
    )
    return (*BASKET, *others)


def receipt(
    shares: pd.DataFrame, basket: Sequence[tuple[str, str, float]] = BASKET
) -> pd.DataFrame:
    """A basket (the example one unless the reader picked theirs) at each food's
    latest national month (fish: its quarter, `months` 3): what you pay and the
    farmer's, traders' and stores' parts, in whole pesos that add up to it, then
    a "Total" row summing each column. A food without a wholesale price that
    month drops out; with none left, the frame is empty."""
    latest = shares[shares["is_latest"] & (shares["geo_code"] == PHILIPPINES)]
    latest = latest.dropna(subset=["wholesale_price"]).set_index("staple")
    lines = []
    for staple, item, quantity in basket:
        if staple not in latest.index:
            continue
        row = latest.loc[staple]
        parts = whole_centavos(
            {
                "farmer": float(row["farmgate_equivalent"]) * quantity,
                "traders": float(row["trader_cut"]) * quantity,
                "stores": float(row["store_cut"]) * quantity,
            }
        )
        lines.append(
            {
                "item": item,
                "month": row["month"],
                "months": int(row["months_in_period"]),
                "pay": sum(parts.values()),
                **parts,
            }
        )
    if not lines:
        return pd.DataFrame()
    rows = pd.DataFrame(lines)
    total = rows[["pay", "farmer", "traders", "stores"]].sum()
    return pd.concat(
        [rows, pd.DataFrame([{"item": "Total", **total}])], ignore_index=True
    )


def short_version(
    shares: pd.DataFrame, verdicts: pd.DataFrame, growth: pd.DataFrame
) -> dict[str, Any]:
    """The numbers behind the short version's bullets, from the same helpers the
    story and who got caught use, so the two never disagree:

    - `hook_month`, `hook_farm`, `hook_store`, `hook_farmer`: the hook's lowest
      farm month, its whole-peso prices and the farmer's centavos then;
    - `farmer`: the typical peso's farmer centavos;
    - `traders_then`, `traders_now`: traders' typical centavos, 2018 and now;
    - `drop_save`: of a ₱10 farm drop, the pesos the typical store passes on;
    - `under_half`, `shared`: foods whose farmer gets under 50 centavos, of the
      foods with a share;
    - `outran`, `foods`: foods whose store price outran the farm since 2018
      (`growth` as `outran` ranks it), of all foods."""
    hooked = hook(shares)
    low = hooked.loc[hooked[FARM].idxmin()]
    rows = farmer_shares(shares)
    parts = parts_then_now(verdicts)
    return {
        "hook_month": pd.Timestamp(str(low["month"])),
        "hook_farm": round(low[FARM]),
        "hook_store": round(low[STORE]),
        "hook_farmer": round(low["farmer"]),
        "farmer": whole_centavos(typical_peso(rows)[0])[FARMER],
        "traders_then": round(parts["trader_part_then"]),
        "traders_now": round(parts["trader_part_now"]),
        "drop_save": round(float(up_and_down(verdicts)["down"].median())),
        "under_half": int((rows["farmer"] < 50).sum()),
        "shared": len(rows),
        "outran": int(growth["outran"].sum()),
        "foods": len(growth),
    }


def newest_move(shares: pd.DataFrame) -> pd.Series | None:
    """The newest month's biggest move in a farmer's share, national: of the
    monthly foods priced in the newest month and the month before, the one whose
    farmer centavos (`now`, `before`, whole) moved most, with `month` and
    `previous`. None when no food has both months or none moved a whole centavo.
    Fish is quarterly, so it never counts."""
    rows = shares[
        (shares["geo_code"] == PHILIPPINES) & (shares["months_in_period"] == 1)
    ]
    rows = rows.dropna(subset=["farmer_share"])
    if rows.empty:
        return None
    month = rows["month"].max()
    previous = month - pd.DateOffset(months=1)
    now = rows[rows["month"] == month].set_index("staple")["farmer_share"]
    before = rows[rows["month"] == previous].set_index("staple")["farmer_share"]
    pairs = pd.DataFrame({"now": now, "before": before}).dropna()
    pairs = (pairs * 100).round().astype(int)
    pairs = pairs[pairs["now"] != pairs["before"]]
    if pairs.empty:
        return None
    moves = (pairs["now"] - pairs["before"]).abs()
    # The biggest move; a tie goes to the food first A to Z.
    staple = moves.sort_index(kind="stable").idxmax()
    row = pairs.loc[staple]
    return pd.Series(
        {
            "staple": staple,
            "month": month,
            "previous": previous,
            "now": int(row["now"]),
            "before": int(row["before"]),
        }
    )


def usual_year(baseline: pd.DataFrame, staple: str) -> pd.DataFrame:
    """One food's 12 months, oldest first, ending at its latest month: the usual
    store price range (`usual_low`, `usual_high`) and the actual price
    (`recent_price`), with a short month name (`label`) for the x axis. Empty when
    the mart has no band for it (no row, or no price level)."""
    rows = baseline[baseline["staple"] == staple].dropna(subset=["usual_low"])
    rows = rows.sort_values("recent_month")
    return rows.assign(label=rows["recent_month"].dt.strftime("%b")).reset_index(
        drop=True
    )


def against_usual(price: float, low: float, high: float) -> str:
    """ "higher" or "lower" only outside the usual range, else "usual"."""
    if price > high:
        return "higher"
    if price < low:
        return "lower"
    return "usual"


def _shown(value: float) -> float:
    # Whole pesos read faster; a cheap item (an egg) keeps its centavos.
    return round(value) if value >= 20 else round(value, 2)


def _pesos(value: float) -> str:
    return f"₱{value:,.0f}" if value >= 20 else f"₱{value:,.2f}"


def season_sentence(baseline: pd.DataFrame, staple: str) -> str | None:
    """The food's usual cheapest and dearest months, then its latest month against
    the usual range for that month. None when the mart has no row for it."""
    rows = baseline[baseline["staple"] == staple]
    if rows.empty:
        return None
    if float(rows["swing"].iloc[0]) < MIN_SEASON_SWING:
        return "Its price barely changes with the season."
    by_month = rows.set_index("calendar_month")["ratio_median"]
    cheap, dear = (
        pd.Timestamp(2000, int(m), 1).strftime("%B")
        for m in (by_month.idxmin(), by_month.idxmax())
    )
    months = f"{staple} is usually cheapest in {cheap} and dearest in {dear}."
    latest = pd.Timestamp(rows["latest_month"].iloc[0])
    now = rows[rows["recent_month"] == latest]
    if now.empty or pd.isna(now["usual_low"].iloc[0]):
        return months
    # Judged on the shown pesos, so "₱69, higher than usual (₱65–₱69)" can't read.
    price, low, high = (
        _shown(float(now[c].iloc[0]))
        for c in ("recent_price", "usual_low", "usual_high")
    )
    name = latest.strftime("%B")
    reading = {
        "usual": f"usual for {name}",
        "higher": f"higher than usual for {name}",
        "lower": f"lower than usual for {name}",
    }[against_usual(price, low, high)]
    return (
        f"{months} {latest:%B %Y}: {_pesos(price)}, {reading} "
        f"({_pesos(low)}–{_pesos(high)})."
    )
