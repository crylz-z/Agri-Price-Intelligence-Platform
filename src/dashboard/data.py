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
# The recipe and basket seeds ship with the app, so it is read from the repo, not from R2.
RECIPES = Path("dbt/seeds/recipes.csv")
BASKET = Path("dbt/seeds/staples.csv")
MAP = Path(__file__).parent / "assets" / "ph_provinces.geojson"
NCR = "130000000"
PHILIPPINES = "000000000"
# Food groups whose members can stand in for each other in a dish (a vegetable
# for a vegetable, a fish for a fish). Rice, spices, beans and fruit can't.
SWAP_GROUPS = {"Vegetables", "Meat", "Fish", "Chicken and eggs"}
# Market aisles for This month's cards: food groups a shopper buys together, so
# a cheap carrot never hides a cheap pork cut. Every staples.csv category is in one.
AISLES = {
    "Meat & fish": {"Meat", "Fish", "Chicken and eggs"},
    "Vegetables": {"Vegetables", "Beans"},
    "Rice & more": {"Rice", "Spices", "Fruit"},
}
# PSA releases monthly; the cron checks daily, so a few hours of staleness is fine.
TTL_SECONDS = 6 * 60 * 60
GEO_LEVELS = ["national", "region", "province"]


# A whole-file deadline: botocore's read_timeout counts per socket read, so a link
# that trickles bytes never trips it and the spinner runs for minutes. Past this,
# fsspec raises FSTimeoutError; the error isn't cached, so a rerun tries again.
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
def load_recipes() -> pd.DataFrame:
    return pd.read_csv(RECIPES)


@st.cache_data
def load_basket() -> pd.DataFrame:
    return pd.read_csv(BASKET)


@st.cache_data
def load_map() -> dict[str, Any]:
    geojson: dict[str, Any] = json.loads(MAP.read_text(encoding="utf-8"))
    return geojson


# Look up any PSA price


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


# Stories


def latest_month(df: pd.DataFrame) -> pd.Timestamp:
    return pd.Timestamp(df.loc[df["geo_level"] == "national", "month"].max())


def at(df: pd.DataFrame, month: pd.Timestamp, geo_level: str) -> pd.DataFrame:
    return df[(df["month"] == month) & (df["geo_level"] == geo_level)]


def in_place(
    df: pd.DataFrame, month: pd.Timestamp, geo_code: str = PHILIPPINES
) -> pd.DataFrame:
    """One month in one place (the whole country by default)."""
    return df[(df["month"] == month) & (df["geo_code"] == geo_code)]


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
    staples: pd.DataFrame,
    month: pd.Timestamp,
    n: int,
    geo_code: str = PHILIPPINES,
    aisle: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The n foods that fell most and the n that rose most in a year, biggest first,
    in one of AISLES or across all foods.

    A food only counts as a good buy if it fell, and as pricier if it rose, so
    either list can be shorter than n.
    """
    rows = in_place(staples, month, geo_code).dropna(subset=["change_year"])
    if aisle:
        rows = rows[rows["category"].isin(AISLES[aisle])]
    fell = rows[rows["change_year"] < 0].nsmallest(n, "change_year")
    rose = rows[rows["change_year"] > 0].nlargest(n, "change_year")
    return fell, rose


def headline(rose: pd.DataFrame, fell: pd.DataFrame) -> str:
    """The biggest rise and fall: 'Repolyo up 34.9%, carrot down 28.5%'.

    Takes year_extremes' lists (biggest first); either may be empty. One decimal,
    so the headline agrees with the cards below it.
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


def history(
    df: pd.DataFrame, key: str, item: str, geo_code: str, months: int | None = None
) -> pd.DataFrame:
    rows = df[(df[key] == item) & (df["geo_code"] == geo_code)].sort_values("month")
    return rows if months is None else rows.tail(months)


def movers(
    df: pd.DataFrame,
    month: pd.Timestamp,
    column: str,
    n: int,
    geo_code: str = PHILIPPINES,
) -> pd.DataFrame:
    """The n largest moves either way, largest rise first."""
    rows = in_place(df, month, geo_code).dropna(subset=[column])
    rows = rows.reindex(rows[column].abs().sort_values(ascending=False).index)
    return rows.head(n).sort_values(column, ascending=False)


def peso_buys(
    staples: pd.DataFrame,
    month: pd.Timestamp,
    geo_code: str = PHILIPPINES,
    staple: str = "Regular rice",
    pesos: float = 100.0,
) -> dict[str, float] | None:
    """How many kg a fixed sum buys now and a year ago, or None without both prices.

    ₱100 at ₱49.90/kg buys 2.00 kg; at last year's ₱40.08/kg it bought 2.49 kg.
    """
    rows = in_place(staples, month, geo_code)
    rows = rows[rows["staple"] == staple].dropna(subset=["price", "price_year_ago"])
    if rows.empty:
        return None
    price, before = float(rows["price"].iloc[0]), float(rows["price_year_ago"].iloc[0])
    return {
        "price": price,
        "price_year_ago": before,
        "kg": pesos / price,
        "kg_year_ago": pesos / before,
    }


def swaps(
    staples: pd.DataFrame,
    month: pd.Timestamp,
    geo_code: str = PHILIPPINES,
    n: int = 3,
    move: float = 0.05,
) -> pd.DataFrame:
    """Up to n pairs: a food that rose by `move` or more in a year, and the food
    in the same group that fell most (by `move` or more). Biggest rise first;
    each alternative is offered once, so the list never repeats itself. Only
    SWAP_GROUPS count: calamansi for red onion (both 'Spices') is no swap.
    """
    rows = in_place(staples, month, geo_code).dropna(subset=["change_year"])
    rows = rows[rows["category"].isin(SWAP_GROUPS)]
    rose = rows[rows["change_year"] >= move].sort_values("change_year", ascending=False)
    fell = rows[rows["change_year"] <= -move].sort_values("change_year")
    pairs: list[dict[str, Any]] = []
    used: set[str] = set()
    for _, row in rose.iterrows():
        options = fell[
            (fell["category"] == row["category"]) & ~fell["staple"].isin(used)
        ]
        if options.empty:
            continue
        pick = options.iloc[0]
        used.add(pick["staple"])
        pairs.append(
            {
                "staple": row["staple"],
                "change_year": row["change_year"],
                "swap": pick["staple"],
                "swap_change": pick["change_year"],
            }
        )
        if len(pairs) == n:
            break
    cols = ["staple", "change_year", "swap", "swap_change"]
    return pd.DataFrame(pairs, columns=cols)


def seasonal_flags(
    seasons: pd.DataFrame, calendar_month: int, threshold: float = 0.05
) -> dict[str, float]:
    """staple -> its usual gap from the year's average in a calendar month, for
    foods whose gap is at least `threshold` either way. Carrot in October: +0.115,
    usually 11.5% above its yearly average."""
    rows = seasons[seasons["calendar_month"] == calendar_month]
    rows = rows[rows["seasonal_index"].abs() >= threshold]
    return dict(zip(rows["staple"], rows["seasonal_index"].astype(float), strict=True))


def area_values(
    df: pd.DataFrame, month: pd.Timestamp, geo_level: str, key: str, item: str
) -> pd.DataFrame:
    """One item's price (or dish cost) in every area of a level, cheapest first."""
    value = "price" if key == "staple" else "dish_cost"
    rows = at(df, month, geo_level)
    rows = rows[(rows[key] == item) & rows[value].notna()]
    rows = rows.rename(columns={value: "value"})
    cols = ["geo_code", "geolocation", "value", "vs_national"]
    return rows[cols].sort_values("value").reset_index(drop=True)


def map_features(
    geojson: dict[str, Any], values: pd.DataFrame, geo_level: str, ncr: pd.DataFrame
) -> dict[str, Any]:
    """Province shapes carrying the value of their province or their region.

    PSA prices NCR only as a region, so at province level NCR's districts take the
    region's value and say so in their label.
    """
    tables = {
        "own": values.set_index("geo_code"),
        "ncr": ncr.set_index("geo_code"),
    }
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
                    # The shape's own codes, for clicking and outlining a place.
                    "geo_code": props["geo_code"],
                    "region_code": props["region_code"],
                    "value": None if row is None else float(row["value"]),
                    "vs_national": None if row is None else float(row["vs_national"]),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def place_basket(
    staples: pd.DataFrame, month: pd.Timestamp, geo_code: str
) -> pd.DataFrame:
    rows = staples[(staples["month"] == month) & (staples["geo_code"] == geo_code)]
    return rows.dropna(subset=["vs_national"]).sort_values("vs_national")


def place_names(staples: pd.DataFrame) -> dict[str, str]:
    """geo code -> name for every region and province or city, A to Z.

    Regions read 'Central Luzon (region)', so a region and a province of the
    same name never look alike in the picker."""
    names = {
        code: f"{name} (region)"
        for code, name in regions(staples).items()
        if code != PHILIPPINES
    }
    rows = staples.loc[staples["geo_level"] == "province", ["geo_code", "geolocation"]]
    rows = rows.drop_duplicates("geo_code")
    names |= dict(zip(rows["geo_code"], rows["geolocation"].astype(str), strict=True))
    return dict(sorted(names.items(), key=lambda kv: kv[1].lower()))


def region_of(staples: pd.DataFrame, geo_code: str) -> str:
    """A province's region code; a region or the country is its own."""
    rows = staples.loc[staples["geo_code"] == geo_code, ["geo_level", "region_code"]]
    if rows.empty or rows["geo_level"].iloc[0] != "province":
        return geo_code
    return str(rows["region_code"].iloc[0])


def typical_gaps(
    staples: pd.DataFrame, month: pd.Timestamp, geo_level: str
) -> pd.DataFrame:
    """Each area's typical gap from the national price, cheapest area first.

    The typical gap is the median of its foods' gaps (vs_national), so one food
    PSA prices oddly can't swing it, and an area that prices fewer foods is still
    compared like with like, food by food. `rank` 1 is the cheapest. `value`
    repeats the gap so the map can draw it like a price.
    """
    rows = at(staples, month, geo_level).dropna(subset=["vs_national"])
    gaps = rows.groupby(["geo_code", "geolocation"], as_index=False).agg(
        vs_national=("vs_national", "median"), foods=("vs_national", "size")
    )
    gaps = gaps.sort_values(["vs_national", "geolocation"]).reset_index(drop=True)
    return gaps.assign(value=gaps["vs_national"], rank=range(1, len(gaps) + 1))


def gap_history(staples: pd.DataFrame, geo_code: str, months: int = 13) -> pd.DataFrame:
    """An area's typical gap and its count of foods above national, month by month."""
    rows = staples[staples["geo_code"] == geo_code].dropna(subset=["vs_national"])
    history = rows.groupby("month", as_index=False).agg(
        typical=("vs_national", "median"),
        dearer=("vs_national", lambda s: int((s > 0).sum())),
        foods=("vs_national", "size"),
    )
    return history.sort_values("month").tail(months).reset_index(drop=True)


def place_headline(basket: pd.DataFrame, where: str) -> str:
    """The food cheapest and the food priciest here against the national price:
    'In Cebu, tilapia costs 25.1% less than the national average, garlic 30.2% more'.

    Takes place_basket's rows (cheapest first). A side with no food on it is
    left out, so a place where everything costs more never names a cheaper food.
    """
    low, high = basket.iloc[0], basket.iloc[-1]
    cheap = low["staple"][0].lower() + low["staple"][1:]
    dear = high["staple"][0].lower() + high["staple"][1:]
    gap = "than the national average"
    if low["vs_national"] < 0 and high["vs_national"] > 0:
        return (
            f"In {where}, {cheap} costs {change_words(low['vs_national'])} {gap}, "
            f"{dear} {change_words(high['vs_national'])}"
        )
    if low["vs_national"] < 0:
        return f"In {where}, {cheap} costs {change_words(low['vs_national'])} {gap}"
    if high["vs_national"] > 0:
        return f"In {where}, {dear} costs {change_words(high['vs_national'])} {gap}"
    return f"In {where}, food costs the same as the national average"


def place_moves(
    staples: pd.DataFrame,
    month: pd.Timestamp,
    geo_code: str,
    months: int = 36,
    min_months: int = 6,
    move: float = 0.05,
) -> pd.DataFrame:
    """Each food here now against its usual gap from the national price.

    `usual` is the median vs_national over the `months` before `month` (foods
    with fewer than `min_months` of them are left out); `shift` is now minus
    usual. Comparing with the national price strips out nationwide swings
    (season, inflation), so a shift is something local: kangkong usually 30%
    above national in NCR but 35% now is a local squeeze. `action` is 'buy' when
    the gap sits `move` or more below usual, 'wait' when `move` or more above,
    else 'usual'. Lowest shift (best deal) first.
    """
    now = place_basket(staples, month, geo_code)
    start = month - pd.DateOffset(months=months)
    past = staples[
        (staples["geo_code"] == geo_code)
        & (staples["month"] < month)
        & (staples["month"] >= start)
    ].dropna(subset=["vs_national"])
    usual = past.groupby("staple")["vs_national"].agg(usual="median", months="size")
    rows = now.merge(usual, left_on="staple", right_index=True)
    rows = rows[rows["months"] >= min_months]
    shift = (rows["vs_national"] - rows["usual"]).round(6)
    action = shift.map(
        lambda s: "buy" if s <= -move else "wait" if s >= move else "usual"
    )
    rows = rows.assign(shift=shift, action=action)
    return rows.sort_values("shift").reset_index(drop=True)


def rank_words(rank: int, total: int, peers: str) -> str:
    """Rank 2 of 18 -> '2nd cheapest of 18 regions'; rank 17 of 18 -> '2nd most
    expensive of 18 regions': whichever end the place is nearer."""
    if rank <= (total + 1) / 2:
        return f"{_ordinal(rank)} cheapest of {total} {peers}"
    return f"{_ordinal(total - rank + 1)} most expensive of {total} {peers}"


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def dish_breakdown(
    staples: pd.DataFrame,
    recipes: pd.DataFrame,
    month: pd.Timestamp,
    geo_code: str,
    dish: str,
) -> pd.DataFrame:
    prices = staples[(staples["month"] == month) & (staples["geo_code"] == geo_code)]
    lines = recipes[recipes["dish"] == dish].merge(
        prices[["staple", "price", "unit"]], on="staple", how="left"
    )
    lines = lines.assign(line_cost=lines["quantity"] * lines["price"])
    return lines.sort_values("line_cost", ascending=False)


def season_extremes(seasons: pd.DataFrame, calendar_month: int) -> pd.DataFrame:
    """Each staple's usual swing in a calendar month, cheapest-than-usual first."""
    rows = seasons[seasons["calendar_month"] == calendar_month]
    return rows.sort_values("seasonal_index").reset_index(drop=True)


def change_words(change: float) -> str:
    """0.245 -> '24.5% more'; -0.031 -> '3.1% less'."""
    if round(change * 100, 1) == 0:
        return "the same"
    return f"{abs(change):.1%} {'more' if change > 0 else 'less'}"


def arrow(change: float) -> str:
    """0.041 -> '↑ 4.1%'; -0.2 -> '↓ 20.0%'. Colour never carries direction alone."""
    if round(change * 100, 1) == 0:
        return "– 0.0%"
    return f"{'↑' if change > 0 else '↓'} {abs(change):.1%}"
