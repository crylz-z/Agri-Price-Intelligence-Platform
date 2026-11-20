"""The dashboard: one page for a reader new to the topic (ADR 14).

"Who's eating the farmer's peso?" in the order a short video would tell it
(ADR 18). Read in order, the headlines tell the story:

1. The hook: onions hit ₱X in January 2023; farmers got ₱Y (farmer_share_monthly,
   the 2023 onion crisis).
2. This year: farmers got X% less for a food; you paid Y% more
   (price_changes_yearly; meat as percent changes only, fish by quarter).
3. Your peso: farmers get X centavos of it, then each food's farmer centavos
   (farmer_share_monthly).
4. The middle: traders now take X centavos of your peso, up from Y; each food's
   farm and store growth since 2018, with inflation (food_verdicts,
   growth_since_2018). The public record sits here once its sources are checked.
5. The ratchet: drop ₱10 at the farm, and you save only ₱X, drawn as an example
   (food_verdicts).
6. Check your food: one food's prices and numbers. Meat, whose farm price is for
   a live animal, shows both prices as a change since 2018 (change_only_monthly).
7. A one-line ending.

Each story section opens with one or two big numbers (`hero`), sized by the CSS
in app.py. Shares are centavos of a peso, real price moves pesos, a growth
percent. No sentence on the page starts with a numeral. The story charts are
ECharts with a brief entry animation (ADR 17) and fade in as they scroll into
view (`reveal`, ADR 18); "Check your food" stays Altair. Under each chart, one
"so what" line (`so_what`) says why it matters, computed like the headline.

One palette, the same in light and dark (ADR 19, ADR 21): blue is the farmer,
amber is the middle (traders and the gap between farm and store), and the store
price is ink, the theme's text colour. Stores' part of the peso is grey. The
theme's blue and orange (`.streamlit/config.toml`) equal FARM and AMBER, so a
coloured word, a big number and a bar always match. Caveats live in the (?)
tooltips.
"""

from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from src.dashboard import data, theme

# One value per role for both themes: each keeps at least 3:1 against the
# light and the dark background. FARM and AMBER equal the theme's blue and orange
# (.streamlit/config.toml), which colour :blue[...] and :orange[...] text.
FARM, AMBER, MUTED = "#4A72E0", "#C77700", "#8A8178"
# Stores' part of the peso: a light grey, named on the bar.
STORE_GREY = "#B5ADA4"
# The store price is ink, the theme's text colour, which the browser picks per
# mode: ECharts hands the theme's chartCategoricalColors (.streamlit/config.toml)
# in order to the series without a colour of their own, so the store series is
# the second uncoloured one and takes [1], the ink. Python learns the theme a
# rerun late, so a colour chosen here would drift after a switch (ADR 19).
STORE_SLOT = 1
# The ratchet draws the store line this far above the farm line, in pesos.
RATCHET_LIFT = 24
SWINGS = 3
# ECharts entry animation (ADR 17): brief and once, since ECharts can't read the
# viewer's reduced-motion setting.
ANIMATION_MS = 800
# The public record (suspects.csv) stays off the page until the owner has
# checked its sources by hand (.claude/rules/dashboard.md).
SHOW_RECORD = False

HOOK_HELP = (
    "National average farm, wholesale and store price of red onion per kilo, "
    "{start:%B} to {end:%B %Y}, from PSA.\n\n"
    "- Late 2022 to early 2023 was the onion crisis: a short harvest, late "
    "imports and, the competition regulator later found, a cartel of importers "
    "and traders.\n"
    "- The chart starts in January: PSA has no farm price for August to "
    "November 2022, and December's farm price sits above the store's."
)
YEAR_HELP = (
    "Each food's national average farm and store price in {month}, against a "
    "year earlier, from PSA. Only foods with both prices in both periods are "
    "shown.\n\n"
    "- Meat: the farm price is for a live animal (a hog, a broiler chicken, "
    "cattle), the store price for a kilo of a cut, so only the percent changes "
    "compare, not the pesos.\n"
    "- Fish: PSA counts the farm price by quarter, so fish compare {quarter} "
    "against the same months a year earlier, the store price averaged over them.\n"
    "- Rice: palay is converted to milled rice at 0.63.\n"
    "- One year can hold a good harvest or a bad one. This shows a pattern, not "
    "why it happens: stores' own costs (rent, wages, power) don't fall with the "
    "farm price."
)
SHARE_HELP = (
    "A farmer's share is the farm price ÷ the store price for the same food and "
    "month, national averages from PSA. Each food shows its latest month with "
    "both prices; fish, its latest quarter.\n\n"
    "- The bar is the average over the {foods} foods with a farm, wholesale and "
    "store price, so its parts add up to one peso.\n"
    "- Traders: wholesale price minus farm price. Stores: store price minus "
    "wholesale price. Transport, storage and spoilage sit in both.\n"
    "- Kangkong has no wholesale price, so it has a dot but isn't in the bar.\n"
    "- Meat isn't here: its farm price is for a live animal, not the cut you "
    "buy.\n"
    "- Rice: palay is converted to milled rice at 0.63, so its share is "
    "approximate.\n"
    "- A farmer's share can top one peso for a month or two when farm prices "
    "briefly beat store prices."
)
MIDDLE_HELP = (
    "Traders' part is the wholesale price minus the farm price, as centavos of "
    "the store price, for the typical food (the median), in 2018 and over the "
    "last 12 months, national averages from PSA.\n\n"
    "- The chart compares each food's average farm and store price in 2018 with "
    "the last 12 months. Inflation is PSA's consumer price index, all items, "
    "over the same months.\n"
    "- Meat (hollow dot): the farm price is for a live animal, so only the "
    "growth compares.\n"
    "- Over the same months, diesel rose {diesel}, transport {transport} and "
    "electricity, gas and other fuels {fuel}. Fuel is one of the middle's costs, "
    "next to wages, rent and spoilage.\n"
    "- This shows a pattern, not who is to blame: a bigger middle can be higher "
    "costs as well as weak competition."
)
MOVES_HELP = (
    "The chart is an example, not a record: the typical food (the median) taken "
    f"through {SWINGS} farm-price rises and falls of ₱10. The store's moves come "
    "from the data, counted over months when a food's farm price was over 15% "
    "higher or lower than a year earlier, national averages from PSA. For each, "
    "the store's peso change is set against the farm's. Both are in 2018 pesos "
    "(divided by the consumer price index), so general inflation doesn't tilt "
    "the result.\n\n"
    "- A peso-for-peso store would show ₱10 both ways.\n"
    '- Each food\'s own numbers are in "Check your food". Foods with under 6 '
    "such months each way are left out, and so is fish: its farm price comes "
    "only by quarter.\n"
    "- This shows a pattern, not why it happens: costs that don't fall, contracts "
    "and spoilage all play a part, as can weak competition."
)


def _once(spec: dict[str, Any]) -> dict[str, Any]:
    """ECharts entry animation (ADR 17): short, played once, no update replay, so
    the finished frame carries the point for anyone who misses the motion."""
    return {
        "animation": True,
        "animationDuration": ANIMATION_MS,
        "animationEasing": "cubicOut",
        "animationDurationUpdate": 0,
        **spec,
    }


def pct(change: float) -> str:
    """A change as a signed whole percent with a true minus sign: −26%, +13%."""
    return f"{change:+.0%}".replace("-", "−")


def when(month: Any, months: Any = 1) -> str:
    """A period in words: "September 2026", or a quarter "July–September 2026"."""
    start = pd.Timestamp(month)
    if int(months) == 1:
        return f"{start:%B %Y}"
    end = start + pd.DateOffset(months=int(months) - 1)
    return f"{start:%B}–{end:%B %Y}"


def hero(section: str, *numbers: tuple[str, str, str]) -> None:
    """One or two big numbers above a section's headline (ADR 18), each a
    (label, value, role). app.py's CSS sizes them; the role colours the value
    through the theme: "farm" blue, "middle" amber, "plain" the theme's ink."""
    with st.container(horizontal=True, gap="large"):
        for i, (label, value, role) in enumerate(numbers):
            with st.container(key=f"hero_{section}_{i}", width="content"):
                st.metric(label, paint(value, role))


def paint(text: str, role: str) -> str:
    """Text in its role's theme colour: "farm" blue, "middle" amber, else as is."""
    colour = {"farm": "blue", "middle": "orange"}.get(role)
    return f":{colour}[{text}]" if colour else text


def reveal(name: str) -> Any:
    """A container that app.py's CSS fades in as it scrolls into view (ADR 18)."""
    return st.container(key=f"reveal_{name}")


def hook_chart(rows: pd.DataFrame) -> dict[str, Any]:
    """The hook: farm (blue) and store (ink) price by month, the gap between them
    a shaded amber band, the first month's and the farm's lowest month's prices
    labelled on the lines."""
    months = [f"{m:%b}" for m in rows["month"]]
    low = int(rows[data.FARM].idxmin())
    marked = {0, low}

    def points(column: str, place: str) -> list[dict[str, Any]]:
        return [
            {
                "value": round(float(v), 2),
                "label": {
                    "show": i in marked,
                    "position": place,
                    "formatter": f"₱{v:,.0f}",
                    "fontWeight": 800,
                    "fontSize": 15,
                },
            }
            for i, v in enumerate(rows[column])
        ]

    def line(name: str, column: str, colour: str | None, place: str) -> dict[str, Any]:
        """A price line; without a colour it takes the theme's (the store's ink)."""
        paint = {"color": colour} if colour else {}
        return {
            "type": "line",
            "name": name,
            "data": points(column, place),
            **paint,
            "lineStyle": {"width": 3},
            "symbolSize": 8,
            "endLabel": {
                "show": True,
                "formatter": "{a}",
                "fontWeight": 700,
                "color": "inherit",
                "distance": 8,
            },
            "z": 3,
        }

    gap = (rows[data.STORE] - rows[data.FARM]).clip(lower=0)
    band = {
        "type": "line",
        "stack": "gap",
        "silent": True,
        "symbol": "none",
        "lineStyle": {"opacity": 0},
        "tooltip": {"show": False},
    }
    top = float(rows[data.STORE].max())
    return _once(
        {
            "grid": {"left": 8, "right": 96, "top": 28, "bottom": 24},
            "xAxis": {
                "type": "category",
                "boundaryGap": False,
                "data": months,
                "axisTick": {"show": False},
            },
            "yAxis": {"type": "value", "show": False, "min": 0, "max": top * 1.12},
            "tooltip": {"trigger": "item", "formatter": "{a}, {b}: ₱{c} a kilo"},
            # The store line second (STORE_SLOT); the band's two series stack
            # in series order around it.
            "series": [
                {
                    **band,
                    "name": "base",
                    "data": [round(v, 2) for v in rows[data.FARM]],
                },
                line("store price", data.STORE, None, "top"),
                {
                    **band,
                    "name": "the gap",
                    "data": [round(v, 2) for v in gap],
                    "areaStyle": {"color": AMBER, "opacity": 0.35},
                },
                line("farm price", data.FARM, FARM, "bottom"),
            ],
        }
    )


def year_chart(rows: pd.DataFrame) -> dict[str, Any]:
    """Each food's farm (blue) and store (ink) change over the past year, as bars
    from a zero line, biggest split on top. The store series is second
    (STORE_SLOT) and uncoloured, so it takes the theme's ink."""

    def bars(column: str, colour: str | None) -> list[dict[str, Any]]:
        return [
            {
                "value": round(v * 100, 1),
                **({"itemStyle": {"color": colour}} if colour else {}),
                "label": {
                    "position": "right" if v >= 0 else "left",
                    "formatter": pct(v),
                },
            }
            for v in rows[column]
        ]

    values = pd.concat([rows["farm_change"], rows["store_change"]]) * 100
    # Room beyond the longest bars for their labels.
    low, high = min(0.0, values.min()) - 14, max(0.0, values.max()) + 14
    label = {"show": True, "fontWeight": 700}
    return _once(
        {
            "grid": {"left": 4, "right": 4, "top": 4, "bottom": 4},
            "xAxis": {"type": "value", "min": low, "max": high, "show": False},
            "yAxis": {
                "type": "category",
                "inverse": True,
                "data": list(rows["staple"]),
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            },
            "tooltip": {"trigger": "item", "formatter": "{b}, {a}: {c}%"},
            "series": [
                {
                    "type": "bar",
                    "name": "farm price",
                    "barWidth": 12,
                    "barGap": "30%",
                    "data": bars("farm_change", FARM),
                    "label": label,
                    "markLine": {
                        "symbol": ["none", "none"],
                        "silent": True,
                        "label": {"show": False},
                        "lineStyle": {"color": MUTED, "type": "solid", "width": 1},
                        "data": [{"xAxis": 0}],
                    },
                },
                {
                    "type": "bar",
                    "name": "store price",
                    "barWidth": 12,
                    "data": bars("store_change", None),
                    "label": label,
                },
            ],
        }
    )


def peso_chart(cents: dict[str, int], foods: int) -> dict[str, Any]:
    """The typical peso as one fat bar: farmer (blue), traders (amber, the
    middle) and stores (grey), each part's centavos big inside it. The bars grow
    in from the left."""
    words = {data.FARMER: "#FFFFFF", data.TRADERS: "#FFFFFF", data.STORES: "#24211E"}
    colour = {data.FARMER: FARM, data.TRADERS: AMBER, data.STORES: STORE_GREY}
    names = list(cents)
    series = [
        {
            "type": "bar",
            "name": name,
            "stack": "peso",
            "barWidth": 76,
            "data": [cents[name]],
            "itemStyle": {
                "color": colour[name],
                "borderRadius": [8, 0, 0, 8]
                if i == 0
                else [0, 8, 8, 0]
                if i == len(names) - 1
                else 0,
            },
            "label": {
                "show": True,
                "position": "insideLeft",
                "distance": 10,
                "formatter": "{n|{c}¢}\n{w|{a}}",
                "rich": {
                    "n": {"fontSize": 24, "fontWeight": 800, "color": words[name]},
                    "w": {"fontSize": 12, "fontWeight": 600, "color": words[name]},
                },
            },
            "emphasis": {"disabled": True},
        }
        for i, name in enumerate(names)
    ]
    return _once(
        {
            "grid": {"left": 0, "right": 0, "top": 0, "bottom": 0},
            "xAxis": {"type": "value", "min": 0, "max": 100, "show": False},
            "yAxis": {"type": "category", "data": ["peso"], "show": False},
            "tooltip": {
                "trigger": "item",
                "formatter": "{a}: {c} centavos of every peso<br/>"
                f"Average of the {foods} foods with a farm, wholesale and store price",
            },
            "series": series,
        }
    )


def farmer_dots(rows: pd.DataFrame, typical: float) -> dict[str, Any]:
    """Each food's farmer centavos as a blue dot, lowest on top, with a dashed
    line at the typical peso's. Only the farmer's part is drawn, so a food without
    a wholesale price (kangkong) fits like any other."""
    top = max(100, int(-(-rows["farmer"].max() // 10) * 10))
    return _once(
        {
            "grid": {"left": 4, "right": 4, "top": 26, "bottom": 4},
            "xAxis": {
                "type": "value",
                "min": 0,
                "max": top,
                "interval": 50,
                "axisLabel": {"formatter": "{value}¢"},
                "splitLine": {"lineStyle": {"opacity": 0.5}},
            },
            # Food names on the left; each food's centavos as a column on the
            # right, clear of the dots and the dashed typical line.
            "yAxis": [
                {
                    "type": "category",
                    "inverse": True,
                    "data": list(rows["staple"]),
                    "axisTick": {"show": False},
                    "axisLine": {"show": False},
                },
                {
                    "type": "category",
                    "inverse": True,
                    "position": "right",
                    "data": [str(round(v)) for v in rows["farmer"]],
                    "axisTick": {"show": False},
                    "axisLine": {"show": False},
                    "axisLabel": {"fontWeight": 700},
                },
            ],
            "tooltip": {
                "trigger": "item",
                "formatter": "{b}: {c} centavos to the farmer",
            },
            "series": [
                {
                    "type": "bar",
                    "name": "farmer",
                    "barWidth": 2,
                    "data": [round(v) for v in rows["farmer"]],
                    "itemStyle": {"color": FARM, "opacity": 0.35},
                    "silent": True,
                    "tooltip": {"show": False},
                },
                {
                    "type": "scatter",
                    "name": "farmer",
                    "symbolSize": 13,
                    "data": [round(v) for v in rows["farmer"]],
                    "itemStyle": {"color": FARM},
                    "emphasis": {"scale": 1.3},
                    "markLine": {
                        "symbol": ["none", "none"],
                        "silent": True,
                        "lineStyle": {"color": MUTED, "type": "dashed", "width": 1.5},
                        "label": {
                            "position": "start",
                            "distance": 6,
                            "formatter": f"typical {typical:.0f}¢",
                            "color": MUTED,
                            "fontWeight": 600,
                        },
                        "data": [{"xAxis": round(typical, 1)}],
                    },
                },
            ],
        }
    )


def middle_chart(rows: pd.DataFrame, inflation: float) -> dict[str, Any]:
    """Each food's growth since 2018 as a dumbbell: the farm price (blue dot,
    hollow for meat's live animal) and the store price (ink dot), joined by an
    amber bar where the store grew faster (the middle grew) and a grey one
    where it didn't, with inflation as a line across. The store series is
    second (STORE_SLOT) and uncoloured, so it takes the theme's ink."""
    foods = list(rows["staple"])

    def dots(column: str, ahead: pd.Series) -> list[dict[str, Any]]:
        return [
            {
                "value": [round(v * 100, 1), food],
                "symbol": "emptyCircle" if hollow else "circle",
                "label": {
                    "show": True,
                    "position": "right" if lead else "left",
                    "formatter": pct(v),
                    "fontWeight": 700,
                    "color": "inherit",
                },
            }
            for v, food, lead, hollow in zip(
                rows[column],
                foods,
                ahead,
                rows["change_only"] & (column == "farm_change"),
            )
        ]

    store_ahead = rows["store_change"] >= rows["farm_change"]
    links = [
        [
            {
                "coord": [round(f * 100, 1), food],
                "lineStyle": {"color": AMBER if up else MUTED},
            },
            {"coord": [round(s * 100, 1), food]},
        ]
        for f, s, food, up in zip(
            rows["farm_change"], rows["store_change"], foods, rows["outran"]
        )
    ]
    values = pd.concat([rows["farm_change"], rows["store_change"]]) * 100
    low, high = min(0.0, float(values.min())), float(values.max())
    # Room either side for the labels, even at phone width.
    pad = 0.3 * (high - low)
    return _once(
        {
            "grid": {"left": 4, "right": 4, "top": 28, "bottom": 4},
            "xAxis": {
                "type": "value",
                "min": low - pad,
                "max": high + pad,
                "show": False,
            },
            "yAxis": {
                "type": "category",
                "inverse": True,
                "data": foods,
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            },
            "tooltip": {"trigger": "item", "formatter": "{a}: {c}%"},
            "series": [
                # The bars between the dots, in an empty series of their own so
                # they draw under the dots.
                {
                    "type": "scatter",
                    "name": "the middle",
                    "data": [],
                    "z": 1,
                    "markLine": {
                        "symbol": ["none", "none"],
                        "silent": True,
                        "animation": False,
                        "lineStyle": {"width": 5, "type": "solid", "opacity": 0.85},
                        "label": {"show": False},
                        "data": links,
                    },
                },
                {
                    "type": "scatter",
                    "name": "store price since 2018",
                    "symbolSize": 11,
                    "data": dots("store_change", store_ahead),
                    "z": 3,
                    "markLine": {
                        "symbol": ["none", "none"],
                        "silent": True,
                        "lineStyle": {"color": MUTED, "type": "dashed", "width": 1.5},
                        "label": {
                            "position": "start",
                            "formatter": f"Inflation {pct(inflation)}",
                            "fontWeight": 700,
                        },
                        "data": [{"xAxis": round(inflation * 100, 1)}],
                    },
                },
                {
                    "type": "scatter",
                    "name": "farm price since 2018",
                    "symbolSize": 11,
                    "itemStyle": {"color": FARM, "borderWidth": 2},
                    "data": dots("farm_change", ~store_ahead),
                    "z": 3,
                },
            ],
        }
    )


def ratchet_chart(up: float, down: float) -> dict[str, Any]:
    """The typical food's farm price (blue) rising and falling ₱10, SWINGS times,
    and its store price (ink) following: up `up`, down only `down`. Both lines
    draw themselves left to right; a dashed line marks where each started and an
    amber bracket (the middle) the store's climb at the end."""
    steps = data.ratchet(up, down, SWINGS)
    last = int(steps["step"].max())

    def points(line: str, lift: float) -> list[list[float]]:
        rows = steps[steps["line"] == line]
        return [[int(s), float(p) + lift] for s, p in zip(rows["step"], rows["price"])]

    farm, store = points(data.FARM, 0), points(data.STORE, RATCHET_LIFT)
    creep = store[-1][1] - RATCHET_LIFT

    def line(
        name: str, pts: list[list[float]], colour: str | None, base: float, end: str
    ) -> dict[str, Any]:
        """A price line; without a colour it takes the theme's (the store's ink)."""
        paint = {"color": colour} if colour else {}
        marks: list[Any] = [
            [
                {"coord": [0, base], "lineStyle": {"type": "dashed", "width": 1.2}},
                {"coord": [last, base]},
            ]
        ]
        if pts[-1][1] > base:
            # The store's climb: an amber bracket from where it started to where
            # it ended, the part the middle kept.
            marks.append(
                [
                    {
                        "coord": [last, base],
                        "lineStyle": {"width": 5, "type": "solid", "color": AMBER},
                        "label": {"show": False},
                    },
                    {"coord": [last, pts[-1][1]]},
                ]
            )
        return {
            "type": "line",
            "name": name,
            "data": pts,
            "silent": True,
            "symbol": "circle",
            "symbolSize": 8,
            **paint,
            "lineStyle": {"width": 3},
            "endLabel": {
                "show": True,
                "formatter": end,
                "fontWeight": 700,
                "fontSize": 13,
                "distance": 10,
            },
            "markLine": {
                "symbol": ["none", "none"],
                "silent": True,
                "animation": False,
                "lineStyle": {"width": 1.5},
                "label": {
                    "show": True,
                    "position": "insideStartBottom",
                    "formatter": name,
                    "color": "inherit",
                    "fontWeight": 700,
                    "fontSize": 13,
                },
                "data": marks,
            },
        }

    return _once(
        {
            "animationEasing": "linear",
            "grid": {"left": 4, "right": 112, "top": 16, "bottom": 22},
            "xAxis": {"type": "value", "min": 0, "max": last, "show": False},
            "yAxis": {
                "type": "value",
                "min": -6,
                "max": RATCHET_LIFT + max(creep, 0) + 16,
                "show": False,
            },
            "tooltip": {"show": False},
            "series": [
                # Both uncoloured: the farm takes the palette's blue, the store
                # its ink (STORE_SLOT).
                line("Farm price", farm, None, 0, "back to start"),
                line(
                    "Store price",
                    store,
                    None,
                    RATCHET_LIFT,
                    f"+₱{creep:.0f} higher" if creep > 0 else "back to start",
                ),
            ],
        }
    )


def food_chart(series: pd.DataFrame, unit: str) -> Any:
    """Farm, wholesale and store price by month, in the theme's first three
    chart colours: farm blue, store ink, wholesale amber (what traders sell
    for, the middle's colour). The theme picks the ink per mode."""
    return (
        alt.Chart(series)
        .mark_line(strokeWidth=2.5)
        .encode(
            x=alt.X(
                "month:T",
                title=None,
                axis=alt.Axis(grid=False, format="%Y", tickCount="year"),
            ),
            y=alt.Y(
                "price:Q",
                title=None,
                axis=alt.Axis(format=",.0f", labelExpr="'₱' + datum.label"),
            ),
            color=alt.Color(
                "line:N",
                scale=alt.Scale(domain=[data.FARM, data.STORE, data.WHOLESALE]),
                legend=alt.Legend(
                    title=None,
                    orient="top",
                    values=[data.FARM, data.WHOLESALE, data.STORE],
                ),
            ),
            tooltip=[
                alt.Tooltip("line:N", title="Price"),
                alt.Tooltip("month:T", format="%B %Y", title="Month"),
                alt.Tooltip("price:Q", format=",.2f", title=f"₱ per {unit}"),
            ],
        )
        .properties(height=280)
    )


def change_chart(series: pd.DataFrame) -> Any:
    """A change-only food's farm (blue) and store (ink) price as a change from
    2018, with a zero line: percent, never pesos, since the products differ."""
    lines = (
        alt.Chart(series)
        .mark_line(strokeWidth=2.5)
        .encode(
            x=alt.X(
                "month:T",
                title=None,
                axis=alt.Axis(grid=False, format="%Y", tickCount="year"),
            ),
            y=alt.Y("change:Q", title=None, axis=alt.Axis(format="+.0%")),
            color=alt.Color(
                "line:N",
                # Blue and ink: the theme's first two chart colours.
                scale=alt.Scale(domain=[data.FARM, data.STORE]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("line:N", title="Price"),
                alt.Tooltip("month:T", format="%B %Y", title="Month"),
                alt.Tooltip("change:Q", format="+.0%", title="Since 2018"),
            ],
        )
    )
    zero = (
        alt.Chart(pd.DataFrame({"change": [0.0]}))
        .mark_rule(color=MUTED, strokeDash=[4, 4])
        .encode(y="change:Q")
    )
    return (zero + lines).properties(height=280)


def moved(change: float) -> str:
    """A change in words: "rose 24%", "fell 19%", "stayed flat"."""
    if round(change * 100) == 0:
        return "stayed flat"
    return f"{'rose' if change > 0 else 'fell'} {abs(change):.0%}"


def so_what(text: str) -> None:
    """The line under a chart that says why it matters."""
    st.markdown(f":material/lightbulb: {text}")


def record(claims: pd.DataFrame) -> None:
    """The public record about the middle, worded as each source words it."""
    st.subheader("On the record")
    for claim in claims.itertuples():
        st.markdown(
            f"{claim.claim} :gray[{claim.status}. "
            f"[{claim.source_name}, {claim.source_date:%d %b %Y}]({claim.source_url})]"
        )


def case_page() -> None:
    shares = data.load(data.SHARES)
    verdicts = data.load(data.VERDICTS)
    changes = data.load(data.CHANGES)
    change_only = data.load(data.CHANGE_ONLY)
    growth = data.outran(data.load(data.GROWTH))
    rows = data.farmer_shares(shares)
    month = pd.Timestamp(shares["month"].max())

    with st.container(
        horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"
    ):
        # No sentence starts with a numeral, so the count follows the place.
        st.caption(
            f"Philippines · {len(growth)} everyday foods · PSA prices to {month:%B %Y}"
        )
        theme.theme_button()
    st.title("Who's eating the farmer's peso?")

    hook_section(shares)
    year_section(changes)
    typical = peso_section(rows)
    middle_section(verdicts, growth)
    moves = ratchet_section(verdicts)

    # 6. Check your food
    st.space("large")
    st.header("Check your food")
    meat = set(growth.loc[growth["change_only"], "staple"])
    foods = list(growth["staple"])
    staple = str(
        st.selectbox(
            "Food",
            foods,
            index=foods.index(data.HOOK_FOOD) if data.HOOK_FOOD in foods else 0,
            key="food",
            bind="query-params",
            label_visibility="collapsed",
            width=260,
        )
    )
    if staple in meat:
        change_only_food(change_only, changes, staple)
    else:
        share_food(staple, rows, verdicts, moves, shares, typical)

    # 7. The ending
    st.space("large")
    st.subheader(
        f"Farmers get {typical} centavos of your peso. Next time a price jumps, ask "
        "who kept the difference."
    )

    st.divider()
    released = (
        shares[["farmgate_released_at", "retail_released_at", "wholesale_released_at"]]
        .max()
        .max()
    )
    st.caption(
        f"Farm, wholesale and store prices: PSA OpenSTAT, latest release "
        f"{pd.Timestamp(released):%d %b %Y}. Inflation and diesel: PSA consumer "
        "price index (2018 = 100)."
    )


def hook_section(shares: pd.DataFrame) -> None:
    """1. The hook: the 2023 onion crisis, the dearest month and the crash."""
    rows = data.hook(shares)
    if rows.empty:
        return
    peak = rows.iloc[0]
    low = rows.loc[rows[data.FARM].idxmin()]
    food = data.HOOK_FOOD.split()[-1] + "s"
    hero(
        "hook",
        (
            f"Onions in the store, {peak['month']:%b %Y}",
            f"₱{peak[data.STORE]:.0f}",
            "plain",
        ),
        ("The farmer got", f"₱{peak[data.FARM]:.0f}", "farm"),
    )
    st.header(
        f"In {peak['month']:%B %Y}, {food} hit ₱{peak[data.STORE]:.0f} a kilo. "
        f"Farmers got :blue[₱{peak[data.FARM]:.0f}].",
        help=HOOK_HELP.format(start=data.HOOK_START, end=data.HOOK_END),
    )
    st.markdown(
        f"By {low['month']:%B}, the :blue[**farm price**] had crashed to "
        f"₱{low[data.FARM]:.0f}. The **store price** was still ₱{low[data.STORE]:.0f}. "
        "The :orange[**shaded gap**] between them is what traders and stores kept."
    )
    with reveal("hook"):
        st.echarts_chart(
            hook_chart(rows),
            height=280,
            key="hook_chart",
            alt=f"Red onion, {data.HOOK_START:%B} to {data.HOOK_END:%B %Y}: the store "
            f"price fell from ₱{peak[data.STORE]:.0f} to ₱{low[data.STORE]:.0f} while "
            f"the farm price fell from ₱{peak[data.FARM]:.0f} to ₱{low[data.FARM]:.0f}",
        )
    so_what(
        f"So even at the peak, farmers got only {peak['farmer']:.0f} centavos of "
        f"every peso. When the price crashed, that fell to {low['farmer']:.0f}."
    )


def year_section(changes: pd.DataFrame) -> None:
    """2. This year: the farm price fell, the store price didn't follow."""
    fallen = data.farm_fell(changes)
    st.space("large")
    if fallen.empty:
        st.header("This year, no food got cheaper at the farm")
        st.caption("Every farm price rose over the past year.")
        return
    top = fallen.iloc[0]
    food = str(top["staple"]).lower()
    farm_food = top["farm_name"] if pd.notna(top["farm_name"]) else food
    store = float(top["store_change"])
    hero(
        "year",
        (f"Farm price, {farm_food}", pct(top["farm_change"]), "farm"),
        (f"Store price, {food}", pct(store), "plain"),
    )
    you = (
        f"You paid {store:.0%} more."
        if round(store * 100) > 0
        else f"You paid only {-store:.0%} less."
        if round(store * 100) < 0
        else "You paid the same."
    )
    monthly = fallen[fallen["months_in_period"] == 1]
    sample = monthly.iloc[0] if len(monthly) else top
    quarterly = changes[changes["months_in_period"] > 1]
    quarter = (
        when(quarterly["month"].max(), quarterly["months_in_period"].max())
        if len(quarterly)
        else "the latest quarter"
    )
    st.header(
        f"Farmers got :blue[{-top['farm_change']:.0%} less] for {food} this year. "
        f"{you}",
        help=YEAR_HELP.format(month=when(sample["month"]), quarter=quarter),
    )
    st.markdown(
        "Each food whose :blue[**farm price**] fell from "
        f"{pd.Timestamp(sample['month_year_ago']):%B %Y} to "
        f"{pd.Timestamp(sample['month']):%B %Y}, beside its **store price**."
    )
    with reveal("year"):
        st.echarts_chart(
            year_chart(fallen),
            height=40 * len(fallen) + 16,
            key="year_chart",
            alt=f"Foods whose farm price fell over the past year: {food}'s fell "
            f"{pct(top['farm_change'])} while its store price moved {pct(store)}",
        )
    rose = int((fallen["store_change"] > 0).sum())
    so_what(
        f"So for {rose} of {len(fallen)} foods, the farmer's drop never reached "
        "you: the store price went up instead."
        if rose
        else "So store prices fell too, but by less than the farmer's."
    )


def peso_section(rows: pd.DataFrame) -> int:
    """3. Your peso: the typical peso, then each food's farmer part. Returns the
    typical farmer's centavos."""
    low = rows.iloc[0]
    peso, averaged = data.typical_peso(rows)
    cents = data.whole_centavos(peso)
    typical = cents[data.FARMER]
    st.space("large")
    hero("peso", ("The farmer's part of a peso", f"{typical}¢", "farm"))
    st.header(
        f"Farmers get :blue[{typical} centavos] of your peso",
        help=SHARE_HELP.format(foods=averaged),
    )
    st.markdown(
        "The bar splits a typical peso between the :blue[**farmer**], "
        ":orange[**traders**] and stores. Below it, each food's farmer part, lowest "
        f"first: {low['staple'].lower()} gets {low['farmer']:.0f}."
    )
    with reveal("peso"):
        st.echarts_chart(
            peso_chart(cents, averaged),
            height=84,
            key="peso_chart",
            alt=f"A typical peso: {cents[data.FARMER]} centavos to the farmer, "
            f"{cents[data.TRADERS]} to traders, {cents[data.STORES]} to stores",
        )
    with reveal("dots"):
        st.echarts_chart(
            farmer_dots(rows, peso[data.FARMER]),
            height=24 * len(rows) + 40,
            key="farmer_dots",
            alt=f"Each food's farmer centavos of every peso, from "
            f"{low['staple'].lower()} at {low['farmer']:.0f} up",
        )
    traders, stores = cents[data.TRADERS], cents[data.STORES]
    after_farm = (
        "So more than half your peso is spent after the farm: "
        if typical < 50
        else "So "
    )
    so_what(
        f"{after_farm}{traders + stores} centavos, {traders} to traders and "
        f"{stores} to stores."
    )
    return typical


def middle_section(verdicts: pd.DataFrame, growth: pd.DataFrame) -> None:
    """4. The middle: traders' part then and now, and each food's farm and store
    growth since 2018."""
    parts = data.parts_then_now(verdicts)
    then, now = round(parts["trader_part_then"]), round(parts["trader_part_now"])
    inflation = float(growth["cpi_change"].iloc[0])
    first = verdicts.iloc[0]
    st.space("large")
    hero(
        "middle",
        ("Traders' part of a peso, 2018", f"{then}¢", "plain"),
        ("Now", f"{now}¢", "middle"),
    )
    st.header(
        f"Traders now take :orange[{now} centavos] of your peso, up from {then}"
        if now > then
        else f"Traders take :orange[{now} centavos] of your peso, as in 2018"
        if now == then
        else f"Traders take :orange[{now} centavos] of your peso, down from {then}",
        help=MIDDLE_HELP.format(
            diesel=pct(first["diesel_change"]),
            transport=pct(first["transport_change"]),
            fuel=pct(first["fuel_change"]),
        ),
    )
    st.markdown(
        "How much each food's :blue[**farm price**] and **store price** grew since "
        "2018. Where the store grew more, the :orange[**bar**] between the dots is "
        "what the middle gained. The dashed line is inflation."
    )
    with reveal("middle"):
        st.echarts_chart(
            middle_chart(growth, inflation),
            height=26 * len(growth) + 40,
            key="middle_chart",
            alt="How much each food's farm and store price grew since 2018, with "
            "inflation",
        )
    ahead = int(growth["outran"].sum())
    so_what(
        f"So for {ahead} of {len(growth)} foods, the store price grew faster than "
        "the farm price. The difference went to the middle, not the farmer."
    )
    if SHOW_RECORD:
        claims = data.load_suspects()
        record(claims[claims["role"] == "suspect"])


def ratchet_section(verdicts: pd.DataFrame) -> pd.DataFrame:
    """5. The ratchet: up fast, down slow, as an example. Returns each food's
    moves for "Check your food"."""
    moves = data.up_and_down(verdicts)
    slower = int((moves["down"] < moves["up"]).sum())
    up, down = float(moves["up"].median()), float(moves["down"].median())
    st.space("large")
    hero("ratchet", ("Of a ₱10 farm drop, you see", f"₱{down:.0f}", "plain"))
    st.header(
        f"Drop ₱10 at the farm, and you save only ₱{down:.0f}"
        if round(down) < 10
        else "Drop ₱10 at the farm, and you save the whole ₱10",
        help=MOVES_HELP,
    )
    most = "Most foods" if slower > len(moves) / 2 else "Some foods"
    st.markdown(
        f"When it rises ₱10, the store rises about ₱{up:.0f}. {most}, {slower} of "
        f"{len(moves)}, come down slower than they go up. Here the typical "
        f":blue[**farm price**] goes up and down {SWINGS} times, and the **store "
        "price** follows. The :orange[**bracket**] is what you still pay extra."
    )
    st.caption(
        ":material/science: An example, not a record: the typical food's moves, "
        f"played out {SWINGS} times."
    )
    with reveal("ratchet"):
        st.echarts_chart(
            ratchet_chart(up, down),
            height=240,
            key="ratchet_chart",
            alt=f"Example: the farm price rises and falls ₱10 {SWINGS} times; the "
            f"store price rises ₱{up:.0f} and falls ₱{down:.0f} each time",
        )
    creep = SWINGS * (round(up) - round(down))
    so_what(
        f"So after {SWINGS} ups and downs the farm price is back where it started, "
        f"but the store price is ₱{creep} higher. Shoppers keep paying for drops "
        "they never see."
        if creep > 0
        else f"So after {SWINGS} ups and downs, both prices end where they started."
    )
    return moves


def change_only_food(monthly: pd.DataFrame, changes: pd.DataFrame, staple: str) -> None:
    """ "Check your food" for meat: its two prices as they are, then how each moved
    over the past year and since 2018. No farmer's share, no peso gap."""
    rows = monthly[monthly["staple"] == staple].sort_values("month")
    now = rows.iloc[-1]
    cut, animal = str(now["store_name"]), str(now["farm_name"])
    with st.container(horizontal=True):
        st.metric(f"You pay, per kg {cut}", f"₱{now['store']:,.2f}", border=True)
        st.metric(
            f"Farm price, per kg {animal}",
            f"₱{now['farm']:,.2f}",
            border=True,
            help=f"The farm price is for a {animal}, the store price for a kilo of "
            f"{cut}: different products, so only their changes compare.",
        )
    st.caption(f"{now['month']:%B %Y}, national average.")
    change = changes[changes["staple"] == staple]
    if len(change):
        st.markdown(
            f"This year the :blue[**{animal} price**] "
            f"{moved(change['farm_change'].iloc[0])}; **{cut}** "
            f"{moved(change['store_change'].iloc[0])}. The chart shows how each moved "
            "since 2018."
        )
    series = data.since_2018(monthly, staple)
    st.altair_chart(
        change_chart(series),
        width="stretch",
        alt=f"{staple}: the {animal} price and the {cut} price as a change since "
        "2018, by month",
    )
    last = series[series["month"] == series["month"].max()].set_index("line")
    farm, store = last.loc[data.FARM, "change"], last.loc[data.STORE, "change"]
    if round(store * 100) > round(farm * 100):
        so_what(
            f"So since 2018 what you pay for {cut} {moved(store)}, but the "
            f"{animal} price {moved(farm)}."
        )
    else:
        so_what(
            f"So since 2018 the {animal} price {moved(farm)}; {cut} {moved(store)}."
        )


def share_food(
    staple: str,
    rows: pd.DataFrame,
    verdicts: pd.DataFrame,
    moves: pd.DataFrame,
    shares: pd.DataFrame,
    typical: int,
) -> None:
    """ "Check your food" for a food with a farmer's share: its prices and parts,
    its gap's growth and moves, its price chart and its share against the typical."""
    picked = rows[rows["staple"] == staple]
    verdict = verdicts[verdicts["staple"] == staple].iloc[0]
    unit = "piece" if verdict["unit"] == "pc" else "kg"
    if picked.empty:
        st.caption(f"PSA has no recent farm and store price for {staple.lower()}.")
    else:
        now = picked.iloc[0]
        with st.container(horizontal=True):
            st.metric(
                f"You pay, per {unit}", f"₱{now['retail_price']:,.2f}", border=True
            )
            st.metric(
                "The farmer gets",
                f"₱{now['farmgate_equivalent']:,.2f}",
                border=True,
                help="Rice: palay ÷ 0.63, as milled rice."
                if "rice" in staple
                else None,
            )
            if pd.isna(now["wholesale_price"]):
                gap = max(0.0, now["retail_price"] - now["farmgate_equivalent"])
                st.metric("The gap", f"₱{gap:,.2f}", border=True)
            else:
                st.metric("Traders", f"₱{now['trader_cut']:,.2f}", border=True)
                st.metric("Stores", f"₱{now['store_cut']:,.2f}", border=True)
        st.caption(f"{when(now['month'], now['months_in_period'])}, national average.")
    faster = verdict["verdict"] == "suspicious"
    # A sentence, not a badge: a badge cuts off at phone width.
    grew = f"{verdict['middle_change']:+.0%}"
    st.markdown(
        "Since 2018 its gap grew "
        + (f":orange[**{grew}**]" if faster else f"**{grew}**")
        + f"; inflation was **{verdict['cpi_change']:+.0%}**."
    )
    move = moves[moves["staple"] == staple]
    if len(move):
        up, down = float(move["up"].iloc[0]), float(move["down"].iloc[0])
        fell = f"fell ₱{down:.0f}" if down >= 0 else f"still rose ₱{-down:.0f}"
        st.markdown(
            f"When its farm price rose ₱10, the store price rose ₱{up:.0f}. "
            f"When it fell ₱10, the store price {fell}."
        )
    st.altair_chart(
        food_chart(data.national_series(shares, staple), unit),
        width="stretch",
        alt=f"{staple} farm and store price by month",
    )
    if not picked.empty:
        share = round(float(picked.iloc[0]["farmer"]))
        if share == typical:
            compared = "about the typical share"
        else:
            side = "more" if share > typical else "less"
            compared = f"{side} than the typical {typical}"
        so_what(
            f"So {staple.lower()}'s farmer gets {share} centavos of every peso you "
            f"pay, {compared}."
        )
