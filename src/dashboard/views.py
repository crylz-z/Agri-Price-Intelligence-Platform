"""The dashboard: one page for a reader new to the topic (ADR 14).

"Who's eating the farmer's peso?" in five short sections, in the order a short
video would tell them (ADR 18). Read in order, the headlines tell the story:

1. Farmers got X% less for a food this year; you paid Y% more: the foods whose
   farm price fell over the past year, next to their store price
   (price_changes_yearly, pork included as percent changes only).
2. Farmers get X centavos of your peso: a typical peso split between farmer,
   traders and stores, then each food's farmer centavos (farmer_share_monthly).
3. Drop ₱10 at the farm, and you save only ₱X (food_verdicts).
4. The gap grew faster than inflation for N foods since 2018, with diesel as a
   second yardstick (food_verdicts).
5. Check your food: one food's prices and numbers.

Each story section opens with one or two big numbers (`hero`), sized and
coloured by the CSS in app.py. Shares are centavos of a peso, real price moves
pesos, a year's change percent (section 1, where pork's live-hog price can't be
set peso for peso against a cut). No sentence on the page starts with a numeral.
The story charts are ECharts with a brief entry animation (ADR 17) and fade in
as they scroll into view (`reveal`, ADR 18); "Check your food" stays Altair.

Under each chart, one "so what" line (`so_what`) says why the chart matters,
computed like the headline. The public record (`suspects.csv`) is off the page
until its sources are checked by hand.

One palette, the same in light and dark: blue is the farmer, amber is what
you pay and what to look at (a store price that rose, a food whose gap beat
inflation, darker past diesel). Traders are dark grey, stores light grey,
everything else grey. The theme's blue and orange (`.streamlit/config.toml`) are
set to the same two colours, so a coloured word, a coloured headline number and
a bar always match. Caveats live in the (?) tooltips.
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
# Deep amber, the same hue darker: a gap that grew faster than even diesel.
DEEP = "#A35400"
# Traders and stores: two greys, darker for the step nearer the farm.
TRADER_GREY, STORE_GREY = MUTED, "#B5ADA4"
# The ratchet draws the store line this far above the farm line, in pesos.
RATCHET_LIFT = 24
SWINGS = 3
# ECharts entry animation (ADR 17): brief and once, since ECharts can't read the
# viewer's reduced-motion setting.
ANIMATION_MS = 800

YEAR_HELP = (
    "Each food's national average farm and store price in {month:%B %Y}, against "
    "{earlier:%B %Y}, from PSA. Only foods with both prices in both months are "
    "shown.\n\n"
    "- Pork: the farm price is for a live hog, the store price for a kilo of "
    "kasim, so only the percent changes compare, not the pesos.\n"
    "- Rice: palay is converted to milled rice at 0.63.\n"
    "- One year can hold a good harvest or a bad one. This shows a pattern, not "
    "why it happens: stores' own costs (rent, wages, power) don't fall with the "
    "farm price."
)
SHARE_HELP = (
    "A farmer's share is the farm price ÷ the store price for the same food and "
    "month, national averages from PSA. Each food shows its latest month with "
    "both prices.\n\n"
    "- The bar is the average over the {foods} foods with a farm, wholesale and "
    "store price, so its parts add up to one peso.\n"
    "- Traders: wholesale price minus farm price. Stores: store price minus "
    "wholesale price. Transport, storage and spoilage sit in both.\n"
    "- Kangkong has no wholesale price, so it has a dot but isn't in the bar.\n"
    "- Rice: palay is converted to milled rice at 0.63, so its share is "
    "approximate.\n"
    "- A farmer's share can top one peso for a month or two when farm prices "
    "briefly beat store prices."
)
MOVES_HELP = (
    "The chart is an example, not a record: the typical food (the median) taken "
    f"through {SWINGS} farm-price rises and falls of ₱10. The store's moves come "
    "from the data, counted over months when a food's farm price was over 15% higher or lower than a year "
    "earlier, national averages from PSA. For each, the store's peso change is "
    "set against the farm's. Both are in 2018 pesos (divided by the consumer price "
    "index), so general inflation doesn't tilt the result.\n\n"
    "- A peso-for-peso store would show ₱10 both ways.\n"
    '- Each food\'s own numbers are in "Check your food". Foods with under 6 '
    "such months each way are left out.\n"
    "- This shows a pattern, not why it happens: costs that don't fall, contracts "
    "and spoilage all play a part, as can weak competition."
)
GROWTH_HELP = (
    "The gap is the store price minus the farm price, per kilo: what traders, "
    "transport, storage and stores together take. Compared: the 2018 average and "
    "the last 12 months' average. Inflation: PSA's consumer price index, all "
    "items. A food is marked when its gap grew more than 5 points faster.\n\n"
    "- Diesel is PSA's consumer price index for diesel, over the same months. "
    "Deep amber: the gap grew faster than diesel too. "
    "Fuel is only one of the gap's costs, next to wages, rent and spoilage.\n"
    "- Over the same months, transport rose {transport:+.0%} and electricity, "
    "gas and other fuels {fuel:+.0%}."
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


def hero(section: str, *numbers: tuple[str, str, str]) -> None:
    """One or two big numbers above a section's headline (ADR 18), each a
    (label, value, role). app.py's CSS sizes them; the role colours the value
    through the theme: "farm" blue, "look" amber, "plain" the theme's ink."""
    with st.container(horizontal=True, gap="large"):
        for i, (label, value, role) in enumerate(numbers):
            with st.container(key=f"hero_{section}_{i}", width="content"):
                st.metric(label, paint(value, role))


def paint(text: str, role: str) -> str:
    """Text in its role's theme colour: "farm" blue, "look" amber, else as is."""
    colour = {"farm": "blue", "look": "orange"}.get(role)
    return f":{colour}[{text}]" if colour else text


def reveal(name: str) -> Any:
    """A container that app.py's CSS fades in as it scrolls into view (ADR 18)."""
    return st.container(key=f"reveal_{name}")


def year_chart(rows: pd.DataFrame) -> dict[str, Any]:
    """Each food's farm (blue) and store (amber, grey where it fell too) change
    over the past year, as bars from a zero line, biggest split on top."""

    def bars(column: str, colour: Any) -> list[dict[str, Any]]:
        return [
            {
                "value": round(v * 100, 1),
                "itemStyle": {"color": colour(v)},
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
                    "data": bars("farm_change", lambda v: FARM),
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
                    "data": bars("store_change", lambda v: AMBER if v > 0 else MUTED),
                    "label": label,
                },
            ],
        }
    )


def peso_chart(cents: dict[str, int], foods: int) -> dict[str, Any]:
    """The typical peso as one fat bar: farmer (blue), traders and stores (greys),
    each part's centavos big inside it. The bars grow in from the left."""
    ink = {data.FARMER: "#FFFFFF", data.TRADERS: "#FFFFFF", data.STORES: "#24211E"}
    colour = {data.FARMER: FARM, data.TRADERS: TRADER_GREY, data.STORES: STORE_GREY}
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
                    "n": {"fontSize": 24, "fontWeight": 800, "color": ink[name]},
                    "w": {"fontSize": 12, "fontWeight": 600, "color": ink[name]},
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


def ratchet_chart(up: float, down: float) -> dict[str, Any]:
    """The typical food's farm price (blue) rising and falling ₱10, SWINGS times,
    and its store price (amber) following: up `up`, down only `down`. Both lines
    draw themselves left to right; a dashed line marks where each started and an
    amber bracket the store's climb at the end."""
    steps = data.ratchet(up, down, SWINGS)
    last = int(steps["step"].max())

    def points(line: str, lift: float) -> list[list[float]]:
        rows = steps[steps["line"] == line]
        return [[int(s), float(p) + lift] for s, p in zip(rows["step"], rows["price"])]

    farm, store = points(data.FARM, 0), points(data.STORE, RATCHET_LIFT)
    creep = store[-1][1] - RATCHET_LIFT

    def line(
        name: str, pts: list[list[float]], colour: str, base: float, end: str
    ) -> dict[str, Any]:
        marks: list[Any] = [
            [
                {"coord": [0, base], "lineStyle": {"type": "dashed", "width": 1.2}},
                {"coord": [last, base]},
            ]
        ]
        if pts[-1][1] > base:
            # The store's climb: a bracket from where it started to where it ended.
            marks.append(
                [
                    {
                        "coord": [last, base],
                        "lineStyle": {"width": 4, "type": "solid"},
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
            "color": colour,
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
                "lineStyle": {"color": colour, "width": 1.5},
                "label": {
                    "show": True,
                    "position": "insideStartBottom",
                    "formatter": name,
                    "color": colour,
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
                line("Farm price", farm, FARM, 0, "back to start"),
                line(
                    "Store price",
                    store,
                    AMBER,
                    RATCHET_LIFT,
                    f"+₱{creep:.0f} higher" if creep > 0 else "back to start",
                ),
            ],
        }
    )


def growth_chart(rows: pd.DataFrame, inflation: float, diesel: float) -> dict[str, Any]:
    """Each food's growth in the gap since 2018: amber when it beat inflation,
    deep amber when it beat diesel too, grey otherwise, with inflation (solid)
    and diesel (dashed) as lines across the bars."""

    def colour(change: float, verdict: str) -> str:
        # Whole percents, as data.grew_faster counts and the labels show.
        if round(change * 100) > round(diesel * 100):
            return DEEP
        return AMBER if verdict == "suspicious" else MUTED

    bars = [
        {
            "value": round(change * 100, 1),
            "itemStyle": {"color": colour(change, verdict)},
            "label": {"formatter": pct(change)},
        }
        for change, verdict in zip(rows["middle_change"], rows["verdict"])
    ]
    top = max(rows["middle_change"].max(), diesel) * 100

    def yardstick(name: str, change: float, kind: str, end: str) -> dict[str, Any]:
        return {
            "xAxis": round(change * 100, 1),
            "lineStyle": {"color": MUTED, "type": kind, "width": 2},
            # Inflation's label above the bars, diesel's below, so they don't
            # collide on a phone ("start" is the top: the food axis is inverse).
            "label": {
                "formatter": f"{name} {pct(change)}",
                "position": end,
                "fontWeight": 700,
            },
        }

    return _once(
        {
            "grid": {"left": 4, "right": 4, "top": 28, "bottom": 28},
            "xAxis": {
                "type": "value",
                "min": min(0.0, rows["middle_change"].min() * 100),
                # Room past the longest bar for its label, even at phone width.
                "max": top * 1.25,
                "show": False,
            },
            "yAxis": {
                "type": "category",
                "inverse": True,
                "data": list(rows["staple"]),
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            },
            "tooltip": {"trigger": "item", "formatter": "{b}: the gap grew {c}%"},
            "series": [
                {
                    "type": "bar",
                    "name": "gap",
                    "barWidth": 14,
                    "data": bars,
                    "itemStyle": {"borderRadius": [0, 3, 3, 0]},
                    "label": {"show": True, "position": "right", "fontWeight": 600},
                    "markLine": {
                        "symbol": ["none", "none"],
                        "silent": True,
                        "data": [
                            yardstick("Inflation", inflation, "solid", "start"),
                            yardstick("Diesel", diesel, "dashed", "end"),
                        ],
                    },
                }
            ],
        }
    )


def food_chart(series: pd.DataFrame, unit: str) -> Any:
    """Farm, wholesale and store price by month, in the story's colours: farm
    blue, wholesale grey, store amber."""
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
                scale=alt.Scale(
                    domain=[data.FARM, data.WHOLESALE, data.STORE],
                    range=[FARM, MUTED, AMBER],
                ),
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


def so_what(text: str) -> None:
    """The line under a chart that says why it matters."""
    st.markdown(f":material/lightbulb: {text}")


def case_page() -> None:
    shares = data.load(data.SHARES)
    verdicts = data.load(data.VERDICTS)
    changes = data.load(data.CHANGES)
    rows = data.farmer_shares(shares)
    inflation = float(verdicts["cpi_change"].iloc[0])
    month = pd.Timestamp(rows["month"].max())

    with st.container(
        horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"
    ):
        # No sentence starts with a numeral, so the count follows the place.
        st.caption(
            f"Philippines · {len(rows)} everyday foods · PSA prices to {month:%B %Y}"
        )
        theme.theme_button()
    st.title("Who's eating the farmer's peso?")

    # 1. This year: the farm price fell, the store price didn't follow
    fallen = data.farm_fell(changes)
    if fallen.empty:
        st.header("This year, no food got cheaper at the farm")
        st.caption("Every farm price rose over the past year.")
    else:
        top = fallen.iloc[0]
        food = str(top["staple"]).lower()
        measure = top["farm_measure"]
        farm_food = f"{food} ({measure})" if pd.notna(measure) else food
        store = float(top["store_change"])
        hero(
            "year",
            (f"Farm price, {farm_food}", pct(top["farm_change"]), "farm"),
            (f"Store price, {food}", pct(store), "look" if store > 0 else "plain"),
        )
        you = (
            f"You paid :orange[{store:.0%} more]."
            if round(store * 100) > 0
            else f"You paid only {-store:.0%} less."
            if round(store * 100) < 0
            else "You paid the same."
        )
        st.header(
            f"Farmers got :blue[{-top['farm_change']:.0%} less] for {food} this year. "
            f"{you}",
            help=YEAR_HELP.format(
                month=pd.Timestamp(top["month"]),
                earlier=pd.Timestamp(top["month_year_ago"]),
            ),
        )
        st.markdown(
            "Each food whose :blue[**farm price**] fell from "
            f"{pd.Timestamp(top['month_year_ago']):%B %Y} to "
            f"{pd.Timestamp(top['month']):%B %Y}, beside its :orange[**store "
            "price**], greyed where the store price fell too."
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

    # 2. How much reaches the farmer: the typical peso, then each food's farmer part
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
        "The bar splits a typical peso between the :blue[**farmer**], traders and "
        "stores. Below it, each food's farmer part, lowest first: "
        f"{low['staple'].lower()} gets {low['farmer']:.0f}."
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
    big, small = ("stores", "traders") if stores >= traders else ("traders", "stores")
    after_farm = (
        "So most of your peso is spent after the farm, and " if typical < 50 else "So "
    )
    so_what(
        f"{after_farm}the biggest part goes to {big}: about "
        f"{max(stores, traders)} centavos, against {min(stores, traders)} for "
        f"{small}."
    )

    # 3. Up fast, down slow
    moves = data.up_and_down(verdicts)
    slower = int((moves["down"] < moves["up"]).sum())
    up, down = float(moves["up"].median()), float(moves["down"].median())
    st.space("large")
    hero("ratchet", ("Of a ₱10 farm drop, you see", f"₱{down:.0f}", "look"))
    st.header(
        f"Drop ₱10 at the farm, and you save only :orange[₱{down:.0f}]"
        if round(down) < 10
        else "Drop ₱10 at the farm, and you save the whole ₱10",
        help=MOVES_HELP,
    )
    most = "Most foods" if slower > len(moves) / 2 else "Some foods"
    st.markdown(
        f"When it rises ₱10, the store rises about ₱{up:.0f}. {most}, {slower} of "
        f"{len(moves)}, come down slower than they go up. Here the typical "
        f":blue[**farm price**] goes up and down {SWINGS} times, and the "
        ":orange[**store price**] follows."
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

    # 4. Is the gap growing?
    growth = data.growth_vs_prices(verdicts)
    worse = int((growth["verdict"] == "suspicious").sum())
    first = verdicts.iloc[0]
    diesel = float(first["diesel_change"])
    past_diesel = data.grew_faster(growth, diesel)
    st.space("large")
    hero("gap", ("Foods whose gap beat inflation", f"{worse} of {len(growth)}", "look"))
    st.header(
        f"The gap grew faster than inflation for :orange[{worse} of {len(growth)}] "
        "foods",
        help=GROWTH_HELP.format(
            transport=first["transport_change"], fuel=first["fuel_change"]
        ),
    )
    st.markdown(
        "How much each food's gap grew since 2018, next to inflation and diesel, "
        "the fuel that moves food. :orange[**Amber**] grew faster than inflation; "
        f"the darkest, {past_diesel} foods, grew faster than even diesel."
    )
    with reveal("growth"):
        st.echarts_chart(
            growth_chart(growth, inflation, diesel),
            height=26 * len(growth) + 40,
            key="growth_chart",
            alt="How much the gap between farm and store price grew since 2018, "
            "for each food",
        )
    parts = data.parts_then_now(verdicts)
    trader_grew = parts["trader_part_now"] - parts["trader_part_then"]
    store_grew = parts["store_part_now"] - parts["store_part_then"]
    where = (
        "between farm and market, with traders"
        if trader_grew > store_grew
        else "between market and shelf, at stores"
    )
    so_what(
        f"So the gap grew most {where}. For the typical food, traders' share of "
        f"every peso rose from {parts['trader_part_then']:.0f} to "
        f"{parts['trader_part_now']:.0f} centavos, stores' from "
        f"{parts['store_part_then']:.0f} to {parts['store_part_now']:.0f}."
    )

    # 5. Check your food
    st.space("large")
    st.header("Check your food")
    foods = list(growth["staple"])
    staple = str(
        st.selectbox(
            "Food",
            foods,
            index=foods.index("Red onion") if "Red onion" in foods else 0,
            key="food",
            bind="query-params",
            label_visibility="collapsed",
            width=260,
        )
    )
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
        st.caption(f"{now['month']:%B %Y}, national average.")
    faster = verdict["verdict"] == "suspicious"
    # A sentence, not a badge: a badge cuts off at phone width.
    grew = f"{verdict['middle_change']:+.0%}"
    st.markdown(
        "Since 2018 its gap grew "
        + (f":orange[**{grew}**]" if faster else f"**{grew}**")
        + f"; inflation was **{inflation:+.0%}**."
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
