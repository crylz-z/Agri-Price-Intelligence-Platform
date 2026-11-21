"""The dashboard: one page for a reader new to the topic (ADR 14).

"Who's eating the farmer's peso?" in the order a short video would tell it
(ADR 18). Read in order, the headlines tell the story:

1. The hook: in March 2023, farmers got ₱X for a kilo of onions, stores charged
   ₱Y; where did the gap go? (farmer_share_monthly, the 2023 onion crisis).
2. The chain: farmer, trader, wholesaler, store; what a fair cut pays for; why
   it matters. Hand-written, each fact cited (context.py).
3. Your peso: farmers get X centavos of it; an example receipt split between
   farmer, traders and stores; each food's farmer centavos (farmer_share_monthly).
4. The middle: traders now take X centavos of your peso, up from Y; each food's
   farm and store growth since 2018, with inflation (food_verdicts,
   growth_since_2018).
5. The ratchet: drop ₱10 at the farm, and you save only ₱X, drawn as an example
   (food_verdicts).
6. Who got caught: the public record, rulings first (dbt/seeds/suspects.csv).
7. What can be done: what is being done and where to report. Hand-written,
   each fact cited (context.py).
8. Check your food: one food's prices and numbers. Meat, whose farm price is for
   a live animal, shows both prices as a change since 2018 (change_only_monthly).
9. A one-line ending.

Each story section opens with one or two big numbers (`hero`), sized by the CSS
in app.py. Shares are centavos of a peso, real price moves pesos, a growth
percent. No sentence on the page starts with a numeral. The story charts are
ECharts with a brief entry animation (ADR 17) and fade in as they scroll into
view (`reveal`, ADR 18); "Check your food" stays Altair. Under each chart, one
"so what" line (`so_what`) says why it matters, computed like the headline.

One palette, the same in light and dark (ADR 19, ADR 21): blue is the farmer,
amber is the middle (traders and the gap between farm and store), and the store
price is ink, the theme's text colour. The
theme's blue and orange (`.streamlit/config.toml`) equal FARM and AMBER, so a
coloured word, a big number and a bar always match. Caveats live in the (?)
tooltips.
"""

import math
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from src.dashboard import context, data, theme

# One value per role for both themes: each keeps at least 3:1 against the
# light and the dark background. FARM and AMBER equal the theme's blue and orange
# (.streamlit/config.toml), which colour :blue[...] and :orange[...] text.
FARM, AMBER, MUTED = "#4A72E0", "#C77700", "#8A8178"
# The store price is ink, the theme's text colour, which the browser picks per
# mode: ECharts hands the theme's chartCategoricalColors (.streamlit/config.toml)
# in order to the series without a colour of their own, so the store series is
# the second uncoloured one and takes [1], the ink. Python learns the theme a
# rerun late, so a colour chosen here would drift after a switch (ADR 19).
STORE_SLOT = 1
# The ratchet draws the store line this far above the farm line, in pesos.
RATCHET_LIFT = 24
# The ratchet is a toy (owner, 2026-11-21): the reader's presses, each +1 or −1
# (₱10 up or down at the farm), live in session state. The chart's x axis holds
# RATCHET_MAX presses, so the lines grow rightwards without rescaling, and the
# farm price stops RATCHET_FLOOR pesos below its start.
RATCHET_MOVES = "ratchet_moves"
RATCHET_MAX = 8
RATCHET_FLOOR = -30
# ECharts entry animation (ADR 17): brief and once, since ECharts can't read the
# viewer's reduced-motion setting.
ANIMATION_MS = 800
# The arrow between two steps of the chain (section 2).
CHAIN_ARROW = ":gray[:material/arrow_forward:]"
# The reader's guess of the hook's store price, in session state: unset until
# they press "Show me", which reveals the store price (spec: Engagement).
HOOK_GUESS = "hook_guess"
# Each public-record stage (suspects.csv `stage`) as its card's badge.
STAGES = {
    "ruling": ("Ruling", "gavel"),
    "charge": ("Charged", "description"),
    "finding": ("Finding", "search"),
    "allegation": ("Alleged", "record_voice_over"),
}

# Each tooltip is a few short lines a newcomer reads at a glance: what the
# number is, then only the caveats that change how to read it.
HOOK_HELP = (
    "Red onion, PSA national averages per kilo, {start:%B} to {end:%B %Y}.\n\n"
    "- The 2022–23 crisis: a short harvest, late imports and, the regulator "
    "found, a cartel.\n"
    "- The chart starts in January: PSA's earlier farm prices are missing or "
    "above the store's."
)
SHARE_HELP = (
    "Farm price ÷ store price, PSA national averages, latest month.\n\n"
    "- The average of the {foods} foods with a farm, wholesale and store price.\n"
    "- Meat is left out: its farm price is for a live animal.\n"
    "- Rice's farm price is converted from palay, so it's approximate."
)
MIDDLE_HELP = (
    "Wholesale minus farm price, as centavos of the store price: the typical "
    "food, 2018 against the last 12 months.\n\n"
    "- Diesel rose {diesel} and transport {transport} over the same months, so "
    "part of this is costs.\n"
    "- A pattern, not proof of who is to blame."
)
MOVES_HELP = (
    "From months when a food's farm price moved over 15% in a year, in 2018 "
    "pesos so inflation doesn't tilt it.\n\n"
    "- A fair store would move ₱10 both ways.\n"
    "- A pattern, not proof of why: costs that don't fall play a part too."
)


def _once(spec: dict[str, Any]) -> dict[str, Any]:
    """ECharts entry animation (ADR 17): short, played once, no update replay, so
    the finished frame carries the point for anyone who misses the motion.

    Each series gets the chart's easing too: ECharts gives a line series its own
    linear easing, which overrides the chart's, so a line drew at full speed to a
    dead stop (ticket 08)."""
    chart = {
        "animation": True,
        "animationDuration": ANIMATION_MS,
        "animationEasing": "cubicOut",
        "animationDurationUpdate": 0,
        **spec,
    }
    chart["series"] = [
        {"animationEasing": chart["animationEasing"], **series}
        for series in chart["series"]
    ]
    return chart


def signed_peso(change: float) -> str:
    """A peso move with its sign and a true minus sign: +₱2, −₱10."""
    return f"{'+' if change > 0 else '−'}₱{abs(change):,.0f}"


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


def ratchet_chart(up: float, down: float, moves: list[int]) -> dict[str, Any]:
    """The reader's toy: the typical food's farm price (blue) taken ₱10 up or
    down for each press in `moves`, and its store price (ink) following: up
    `up`, down only `down`. A dashed line marks where each started; an amber
    bracket (the middle) marks how far the store ended above a peso-for-peso
    follower. Each press tweens in, so the reader sees their move land."""
    steps = data.ratchet(up, down, moves)

    def points(line: str, lift: float) -> list[list[float]]:
        rows = steps[steps["line"] == line]
        return [[int(s), float(p) + lift] for s, p in zip(rows["step"], rows["price"])]

    farm, store = points(data.FARM, 0), points(data.STORE, RATCHET_LIFT)
    farm_net, store_net = farm[-1][1], store[-1][1] - RATCHET_LIFT
    last = RATCHET_MAX

    def signed(net: float) -> str:
        return "back to start" if net == 0 else signed_peso(net)

    def line(
        name: str, pts: list[list[float]], base: float, end: str, bracket: bool
    ) -> dict[str, Any]:
        """A price line, uncoloured: the theme's palette paints it (STORE_SLOT)."""
        marks: list[Any] = [
            [
                {"coord": [0, base], "lineStyle": {"type": "dashed", "width": 1.2}},
                {"coord": [last, base]},
            ]
        ]
        follower = base + farm_net
        if bracket and pts[-1][1] > follower:
            # What the store kept: an amber bracket from where a peso-for-peso
            # store would be to where this one ended, the part the middle kept.
            marks.append(
                [
                    {
                        "coord": [pts[-1][0], follower],
                        "lineStyle": {"width": 5, "type": "solid", "color": AMBER},
                        "label": {"show": False},
                    },
                    {"coord": [pts[-1][0], pts[-1][1]]},
                ]
            )
        return {
            "type": "line",
            "name": name,
            "data": pts,
            "silent": True,
            "symbol": "circle",
            "symbolSize": 8,
            "lineStyle": {"width": 3},
            "endLabel": {
                "show": bool(moves),
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

    values = [p[1] for p in farm + store]
    return _once(
        {
            "animationEasing": "linear",
            "animationDurationUpdate": 300,
            "animationEasingUpdate": "cubicOut",
            "grid": {"left": 4, "right": 112, "top": 16, "bottom": 22},
            "xAxis": {"type": "value", "min": 0, "max": last, "show": False},
            "yAxis": {
                "type": "value",
                "min": min(values) - 6,
                "max": max(values) + 16,
                "show": False,
            },
            "tooltip": {"show": False},
            "series": [
                # Both uncoloured: the farm takes the palette's blue, the store
                # its ink (STORE_SLOT).
                line("Farm price", farm, 0, signed(farm_net), bracket=False),
                line(
                    "Store price", store, RATCHET_LIFT, signed(store_net), bracket=True
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


def receipt_table(receipt: pd.DataFrame) -> None:
    """The example basket as a receipt: one line per food in whole pesos, then
    the total, captioned with its months (galunggong's is a quarter)."""
    if receipt.empty:
        return
    # Markdown cells: the farmer's and traders' headers take their role colours,
    # and the total row is bold.
    columns = {
        "pay": "You pay",
        "farmer": paint("Farmer", "farm"),
        "traders": paint("Traders", "middle"),
        "stores": "Stores",
    }
    table = receipt.set_index("item").rename_axis(None)[list(columns)]
    table = table.rename(columns=columns).map(lambda pesos: f"₱{pesos:,.0f}")
    table.iloc[-1] = "**" + table.iloc[-1] + "**"
    table = table.rename(index={table.index[-1]: f"**{table.index[-1]}**"})
    st.table(table, border="horizontal")
    periods = {
        str(row.item).split(",")[0].lower(): when(row.month, row.months)
        for row in receipt.iloc[:-1].itertuples()
    }
    usual = max(set(periods.values()), key=list(periods.values()).count)
    others = "; ".join(f"{food} {p}" for food, p in periods.items() if p != usual)
    st.caption(
        ":material/receipt_long: An example basket, at national prices for "
        f"{usual}{f' ({others})' if others else ''}."
    )


def cite(fact: context.Fact) -> str:
    """A hand-written fact's source and year, linked, to follow its sentence."""
    return f":gray[([{fact.source}, {fact.date[:4]}]({fact.url}))]"


def so_what(text: str) -> None:
    """The line under a chart that says why it matters."""
    st.markdown(f":material/lightbulb: {text}")


def record_section() -> None:
    """6. Who got caught: the public record about the middle, rulings first (the
    seed's order), each worded as its source words it, with its status and
    source. Context, so text only."""
    claims = data.load_suspects()
    claims = claims[claims["role"] == "suspect"]
    st.space("large")
    fined = claims.dropna(subset=["fine_php"])
    if not fined.empty:
        latest = fined["source_date"].max()
        hero(
            "record",
            (
                f"Fined so far, {latest:%b %Y}",
                f"₱{fined['fine_php'].sum() / 1e9:.2f} billion",
                "middle",
            ),
        )
    st.header("Who got caught", anchor=False)
    st.markdown(
        "Our prices show where the pesos go, not who takes them. Only regulators, "
        "investigators and lawmakers can name that. This is what they found, "
        "charged or alleged."
    )
    for claim in claims.itertuples():
        label, icon = STAGES[str(claim.stage)]
        with st.container(border=True):
            st.badge(label, icon=f":material/{icon}:", color="gray")
            st.markdown(
                f"{claim.claim} :gray[{claim.status}. [{claim.source_name}, "
                f"{claim.source_date:%d %b %Y}]({claim.source_url})]"
            )


def remedy_section() -> None:
    """7. What can be done: what regulators and the government are doing, and
    where a reader can report. Facts only, no policy positions, each cited.
    Context, so text only."""
    st.space("large")
    st.header("What can be done", anchor=False)
    st.subheader("Being done", anchor=False)
    # Two cards a row, so a phone, which stacks the columns, keeps their order.
    cards = context.BEING_DONE
    for row in range(0, len(cards), 2):
        for column, (title, icon, fact) in zip(
            st.columns(2), cards[row : row + 2], strict=False
        ):
            with column.container(border=True, height="stretch"):
                st.markdown(f"**:material/{icon}: {title}**")
                st.markdown(f"{fact.text} {cite(fact)}")
    st.subheader("Where to report", anchor=False)
    st.link_button(
        "Report a cartel to the PCC",
        context.PCC_PORTAL,
        type="primary",
        icon=":material/campaign:",
    )
    st.markdown("\n".join(f"- {fact.text} {cite(fact)}" for fact in context.REPORT))


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
    st.title("Who's eating the farmer's peso?", anchor=False)

    hook_section(shares)
    chain_section()
    typical = peso_section(shares, rows)
    middle_section(verdicts, growth)
    moves = ratchet_section(verdicts)
    record_section()
    remedy_section()

    # 8. Check your food
    st.space("large")
    st.header("Check your food", anchor=False)
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

    # 9. The ending
    st.space("large")
    st.subheader(
        f"Farmers get {typical} centavos of your peso. Next time a price jumps, ask "
        "who kept the difference.",
        anchor=False,
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
    """1. The hook: the 2023 onion crisis asked as a question, at the farm
    price's lowest month."""
    rows = data.hook(shares)
    if rows.empty:
        return
    first = rows.iloc[0]
    low = rows.loc[rows[data.FARM].idxmin()]
    # Whole pesos, so the gap on screen is the difference of the prices shown.
    farm, store = round(low[data.FARM]), round(low[data.STORE])
    food = data.HOOK_FOOD.split()[-1] + "s"
    farm_number = (f"Farmers got, {low['month']:%b %Y}", f"₱{farm}", "farm")
    farmers_got = (
        f"In {low['month']:%B %Y}, farmers got :blue[₱{farm}] for a kilo of {food}."
    )
    help_text = HOOK_HELP.format(start=data.HOOK_START, end=data.HOOK_END)
    guess = st.session_state.get(HOOK_GUESS)
    if guess is None:
        # The reader guesses the store price before seeing it (spec: Engagement).
        hero("hook", farm_number)
        st.header(
            f"{farmers_got} What do you think stores charged?",
            help=help_text,
            anchor=False,
        )
        st.markdown(f"{context.ONION_VS_MEAT.text} {cite(context.ONION_VS_MEAT)}")
        st.slider(
            "Your guess, a kilo",
            min_value=farm,
            max_value=math.ceil(2 * store / 50) * 50,
            value=farm,
            step=5,
            format="₱%d",
            key="hook_slider",
        )
        st.button(
            "Show me",
            key="hook_show",
            type="primary",
            on_click=lambda: st.session_state.update(
                {HOOK_GUESS: st.session_state["hook_slider"]}
            ),
        )
        return
    hero("hook", farm_number, ("Stores charged", f"₱{store}", "plain"))
    st.header(
        f"{farmers_got} Stores charged ₱{store}. Where did the "
        f":orange[₱{store - farm}] go?",
        help=help_text,
        anchor=False,
    )
    off = store - int(guess)
    st.markdown(
        f"Your guess was ₱{guess}. "
        + (
            f"Stores charged ₱{store}, ₱{abs(off)} {'more' if off > 0 else 'less'}."
            if off
            else "Spot on."
        )
    )
    st.markdown(
        f"{context.ONION_VS_MEAT.text} {cite(context.ONION_VS_MEAT)} "
        f"The :blue[**farm price**] of red onion crashed from "
        f"₱{first[data.FARM]:.0f} in {first['month']:%B} to ₱{farm} by "
        f"{low['month']:%B}. The **store price** was still ₱{store}. The "
        ":orange[**shaded gap**] between them is what traders and stores kept."
    )
    with reveal("hook"):
        st.echarts_chart(
            hook_chart(rows),
            height=280,
            key="hook_chart",
            alt=f"Red onion, {data.HOOK_START:%B} to {data.HOOK_END:%B %Y}: by "
            f"{low['month']:%B} the farm price had fallen to ₱{farm} while the store "
            f"price was ₱{store}",
        )
    so_what(
        f"So in {low['month']:%B}, farmers got only {low['farmer']:.0f} centavos of "
        f"every peso. Even at {first['month']:%B}'s peak, they got "
        f"{first['farmer']:.0f}."
    )


def chain_section() -> None:
    """2. The chain: who stands between farm and store, what a fair cut pays
    for, and why it matters. Context, so text only, each fact cited."""
    st.space("large")
    st.header(
        "Between the farmer and you: traders, wholesalers and stores", anchor=False
    )
    st.markdown(
        "Traders, wholesalers and stores each take a cut of what you pay. On this "
        "page, :orange[**traders**] "
        "means the traders and wholesalers together, everyone between the farm "
        "and the store."
    )
    # Stock columns: side by side on a wide screen, stacked top to bottom on a
    # phone, so the order reads farm to store either way. A narrow column holds
    # the arrow between two steps; app.py's CSS turns it down when they stack.
    columns = st.columns([1, 0.14] * (len(context.CHAIN) - 1) + [1], gap="small")
    for i, (name, icon, fact) in enumerate(context.CHAIN):
        if i:
            with columns[2 * i - 1].container(
                key=f"chain_arrow_{i}",
                height="stretch",
                horizontal_alignment="center",
                vertical_alignment="center",
            ):
                st.markdown(CHAIN_ARROW)
        with columns[2 * i].container(border=True, height="stretch"):
            st.markdown(f"**:material/{icon}: {name}**")
            st.markdown(f"{fact.text} {cite(fact)}")
    st.markdown(
        "A fair cut pays for real work:\n\n"
        + "\n".join(f"- {fact.text} {cite(fact)}" for fact in context.FAIR_CUT)
    )
    so_what(
        "So who keeps the gap matters: farmers and fisherfolk are among the "
        f"poorest Filipinos. {context.POVERTY.text} {cite(context.POVERTY)}"
    )


def peso_section(shares: pd.DataFrame, rows: pd.DataFrame) -> int:
    """3. Your peso: the typical peso as big numbers, the example receipt, then
    each food's farmer part. Returns the typical farmer's centavos."""
    low = rows.iloc[0]
    peso, averaged = data.typical_peso(rows)
    cents = data.whole_centavos(peso)
    typical = cents[data.FARMER]
    st.space("large")
    # Traders' part is section 4's number alone: this one (the latest month's
    # average) differs from its (the last 12 months' median) by a centavo or so.
    hero("peso", ("The farmer's part of a peso", f"{typical}¢", "farm"))
    st.header(
        f"Farmers get :blue[{typical} centavos] of your peso",
        help=SHARE_HELP.format(foods=averaged),
        anchor=False,
    )
    st.markdown(
        "The receipt splits an example basket between the :blue[**farmer**], "
        ":orange[**traders**] and stores. Below it, each food's farmer part, lowest "
        f"first: {low['staple'].lower()} gets {low['farmer']:.0f}."
    )
    receipt_table(data.receipt(shares))
    with reveal("dots"):
        st.echarts_chart(
            farmer_dots(rows, peso[data.FARMER]),
            height=24 * len(rows) + 40,
            key="farmer_dots",
            alt=f"Each food's farmer centavos of every peso, from "
            f"{low['staple'].lower()} at {low['farmer']:.0f} up",
        )
    after = 100 - typical
    so_what(
        f"So more than half your peso, {after} centavos, is spent after the farm, "
        "by traders and stores."
        if after > 50
        else f"So {after} centavos of your peso are spent after the farm, by "
        "traders and stores."
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
        ),
        anchor=False,
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


def ratchet_section(verdicts: pd.DataFrame) -> pd.DataFrame:
    """5. The ratchet: up fast, down slow, as a toy the reader plays. Returns
    each food's moves for "Check your food"."""
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
        anchor=False,
    )
    most = "Most foods" if slower > len(moves) / 2 else "Some foods"
    st.markdown(
        f"When the farm price rises ₱10, stores add about ₱{up:.0f}. {most}, "
        f"{slower} of {len(moves)}, come down slower than they go up. Push the "
        "typical food's :blue[**farm price**] up and down, and watch the **store "
        "price** follow. The :orange[**bracket**] is what you pay extra."
    )
    st.caption(":material/science: An example, not a record: the typical food's moves.")
    ratchet_toy(up, down)
    return moves


def _press(move: int) -> None:
    """Add one press (+1 up, −1 down, 0 start over) to the ratchet toy."""
    pressed = st.session_state.get(RATCHET_MOVES, [])
    st.session_state[RATCHET_MOVES] = [*pressed, move] if move else []


@st.fragment
def ratchet_toy(up: float, down: float) -> None:
    """The ratchet's buttons, chart and so-what. A fragment, so a press reruns
    only this, not the page."""
    pressed: list[int] = st.session_state.get(RATCHET_MOVES, [])
    farm_net = 10 * sum(pressed)
    store_net = sum(round(up) if m > 0 else -round(down) for m in pressed)
    full = len(pressed) >= RATCHET_MAX
    with st.container(horizontal=True):
        st.button(
            "Farm price +₱10",
            key="ratchet_up",
            icon=":material/arrow_upward:",
            disabled=full,
            on_click=_press,
            args=(1,),
        )
        st.button(
            "Farm price −₱10",
            key="ratchet_down",
            icon=":material/arrow_downward:",
            disabled=full or farm_net - 10 < RATCHET_FLOOR,
            on_click=_press,
            args=(-1,),
        )
        st.button(
            "Start over",
            key="ratchet_reset",
            icon=":material/replay:",
            type="tertiary",
            disabled=not pressed,
            on_click=_press,
            args=(0,),
        )
    with reveal("ratchet"):
        st.echarts_chart(
            ratchet_chart(up, down, pressed),
            height=240,
            key="ratchet_chart",
            alt=f"A toy: each press moves the farm price ₱10; the store price "
            f"rises ₱{up:.0f} and falls ₱{down:.0f} each time",
        )
    if not pressed:
        return

    def where(net: float) -> str:
        if net == 0:
            return "back where it started"
        return f"₱{abs(net):.0f} {'higher' if net > 0 else 'lower'}"

    extra = store_net - farm_net
    if extra > 0:
        so_what(
            f"So the farm price is {where(farm_net)}, but the store price is "
            f"{where(store_net)}. You pay ₱{extra:.0f} the farmer never saw."
        )
    elif extra == 0:
        so_what(
            "So far the store price has kept pace with the farm price. Now push "
            "the farm price down."
            if -1 not in pressed
            else "So the store price kept pace with the farm price both ways."
        )
    else:
        so_what(f"So the store price moved ₱{-extra:.0f} less than the farm price.")


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
