"""The dashboard's pages for a reader new to the topic (ADR 14, ADR 25).

"Who's eating the farmer's peso?" in the order a short video would tell it
(ADR 18), split into four pages (`nav.PAGES`, ADR 25). Each page opens with
`masthead` and ends with `footer`. Read in order, the headlines tell the story.

The story (`story_page`), the whole finding in about 90 seconds on a phone:
1. The hook: in March 2023, farmers got ₱X for a kilo of onions, stores charged
   ₱Y; where did the gap go? (farmer_share_monthly, the 2023 onion crisis).
2. The chain: farmer, trader, wholesaler, store, as four cards. Hand-written
   (context.py), cited in the page's Sources expander.
3. Your peso: farmers get X centavos of it; an example receipt split between
   farmer, traders and stores (farmer_share_monthly).
4. It's growing: traders now take X centavos of your peso, up from Y
   (food_verdicts).
5. The ratchet: drop ₱10 at the farm, and you save only ₱X, drawn as an
   example (food_verdicts).
6. The ending: regulators have fined ₱X so far (suspects.csv), on to page 2.

Who got caught (`caught_page`):
1. It's not one food, and it's not new: each food's farmer centavos, then each
   food's farm and store growth since 2018 (growth_since_2018).
2. Who got caught: the public record, rulings first (dbt/seeds/suspects.csv).
3. What can be done: what is being done and where to report, each fact cited.

Check your food (`food_page`): one food's prices and numbers. Meat, whose farm
price is for a live animal, shows both prices as a change since 2018
(change_only_monthly). How it's built is `how.py`.

The word budget (spec): each section has its headline, at most one line under
it and one so-what; detail goes in a tooltip or the Sources expander.

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

from src.dashboard import context, data, nav, theme

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
# The ratchet's example moves, each ₱10 up (+1) or down (−1) at the farm: three
# times up and back, so the farm price ends where it started.
RATCHET_MOVES = (1, -1) * 3
# ECharts entry animation (ADR 17): brief and once, since ECharts can't read the
# viewer's reduced-motion setting.
ANIMATION_MS = 800
# The arrow between two steps of the chain (section 2).
CHAIN_ARROW = ":gray[:material/arrow_forward:]"
# The reader's guess of the hook's store price, in session state: unset until
# they press "Show me", which reveals the store price (spec: Engagement).
HOOK_GUESS = "hook_guess"
# Each page's link to the next (`nav.after`), at its foot.
NEXT = {
    "story": "See who got caught",
    "caught": "Check your food",
    "food": "Read the short version",
    "short": "See how it's built",
    "how": "Back to the story",
}
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
    "- When the farm price rises ₱10, stores add about ₱{up:.0f}. {most}, "
    "{slower} of {foods}, come down slower than they go up.\n"
    "- A fair store would move ₱10 both ways.\n"
    "- A pattern, not proof of why: costs that don't fall play a part too."
)
# The chain's tooltip: who "traders" are on the page, and what a fair cut pays
# for. Each fact is cited in the story's Sources expander.
CHAIN_HELP = (
    "On this page, traders means the traders and wholesalers together, everyone "
    "between the farm and the store.\n\n"
    + "\n".join(f"- {fact.text}" for fact in context.FAIR_CUT)
)
# The facts the story cites in its Sources expander, not inline (spec: Page 1),
# each with a lead-in where it needs one to make sense on its own.
STORY_SOURCES: tuple[tuple[str, context.Fact], ...] = (
    ("", context.ONION_VS_MEAT),
    *((f"**{name}:** ", fact) for name, _, fact in context.CHAIN),
    *(("", fact) for fact in context.FAIR_CUT),
    ("", context.POVERTY),
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


# Each page's chapters, in order: a small grey label above each section fills
# the gap before it, so the space reads as a break, not missing content.
CHAPTERS = {
    "story": (
        "The onion question",
        "Who's in between",
        "Where your peso goes",
        "The middle's growing part",
        "Up fast, down slow",
    ),
    "caught": ("Every food", "Not new", "Who got caught", "What can be done"),
}


def chapter(page: str, name: str) -> None:
    """The label above a section: "Part 2 of 5 · Who's in between". It opens
    with a word, so no sentence on the page starts with a numeral."""
    names = CHAPTERS[page]
    st.caption(f"Part {names.index(name) + 1} of {len(names)} · {name}")


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
                # A dot only where there's a label: the rest trailed the eased
                # line and popped in after it stopped (story v3 ticket 08).
                "symbol": "circle" if i in marked else "none",
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
            "grid": {"left": 4, "right": 20, "top": 26, "bottom": 4},
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


def middle_chart(rows: pd.DataFrame) -> dict[str, Any]:
    """Each food's farm and store growth since 2018 as a dumbbell, in the rows'
    order (`data.outran`: the store's biggest lead first): a blue farm dot and
    an ink store dot, joined by an amber line where the store grew faster (the
    middle grew) and a grey one where it didn't. Each food's label says both
    percents, so no one subtracts in their head, and sits left of the plot on
    two lines, which keeps the plot wide on a phone."""
    farms = [round(f * 100) for f in rows["farm_change"]]
    stores = [round(s * 100) for s in rows["store_change"]]
    labels = [
        f"{{food|{food}}}\n{{growth|farm {pct(f)}, store {pct(s)}}}"
        for food, f, s in zip(
            rows["staple"], rows["farm_change"], rows["store_change"], strict=True
        )
    ]

    def dots(name: str, values: list[int], **extra: Any) -> dict[str, Any]:
        # Uncoloured, farm first: the palette's blue, then the store's ink.
        return {
            "type": "scatter",
            "name": name,
            "symbolSize": 10,
            "z": 3,
            "silent": True,
            "data": [[value, i] for i, value in enumerate(values)],
            **extra,
        }

    segments = [
        [
            {"coord": [f, i], "lineStyle": {"color": AMBER if up else MUTED}},
            {"coord": [s, i]},
        ]
        for i, (f, s, up) in enumerate(zip(farms, stores, rows["outran"], strict=True))
    ]
    return _once(
        {
            "grid": {"left": 4, "right": 12, "top": 4, "bottom": 20},
            "xAxis": {
                "type": "value",
                # Few ticks, and none that would touch, at phone width.
                "splitNumber": 3,
                "axisLabel": {"formatter": "{value}%", "hideOverlap": True},
                "splitLine": {"lineStyle": {"opacity": 0.3}},
            },
            "yAxis": {
                "type": "category",
                "inverse": True,
                "data": labels,
                "axisTick": {"show": False},
                "axisLine": {"show": False},
                "axisLabel": {
                    "align": "left",
                    "margin": 160,
                    "rich": {
                        "food": {"fontSize": 13, "fontWeight": 600, "lineHeight": 17},
                        "growth": {"color": MUTED, "fontSize": 12, "lineHeight": 15},
                    },
                },
            },
            "tooltip": {"show": False},
            "series": [
                dots(
                    "farm growth",
                    farms,
                    markLine={
                        "silent": True,
                        "symbol": "none",
                        "z": 1,
                        "label": {"show": False},
                        "lineStyle": {"width": 3, "type": "solid", "opacity": 1},
                        "data": segments,
                    },
                ),
                dots("store growth", stores),
            ],
        }
    )


def ratchet_chart(up: float, down: float, moves: list[int]) -> dict[str, Any]:
    """An example: the typical food's farm price (blue) taken ₱10 up or down
    for each move in `moves`, and its store price (ink) following: up
    `up`, down only `down`. A dashed line marks where each started; an amber
    bracket (the middle) marks how far the store ended above a peso-for-peso
    follower."""
    steps = data.ratchet(up, down, moves)

    def points(line: str, lift: float) -> list[list[float]]:
        rows = steps[steps["line"] == line]
        return [[int(s), float(p) + lift] for s, p in zip(rows["step"], rows["price"])]

    farm, store = points(data.FARM, 0), points(data.STORE, RATCHET_LIFT)
    farm_net, store_net = farm[-1][1], store[-1][1] - RATCHET_LIFT
    last = len(moves)

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

    values = [p[1] for p in farm + store]
    return _once(
        {
            "animationEasing": "linear",
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


def usual_year_chart(rows: pd.DataFrame, unit: str) -> Any:
    """The past 12 months of store price (ink) over a grey band: the usual price
    for each month in past years, in today's pesos."""
    order = list(rows["label"])
    x = alt.X("label:O", title=None, sort=order, axis=alt.Axis(labelAngle=0))
    # One y for both layers: an unset one on the band drew a second, unformatted
    # axis under the ₱ one.
    scale = alt.Scale(zero=False)
    # Unflushed: the theme nudges the end labels inward, off their gridlines.
    axis = alt.Axis(format=",.0f", labelExpr="'₱' + datum.label", labelFlush=False)
    band = (
        alt.Chart(rows)
        .mark_area(color=MUTED, opacity=0.3)
        .encode(
            x=x,
            y=alt.Y("usual_low:Q", title=None, scale=scale, axis=axis),
            y2="usual_high:Q",
        )
    )
    line = (
        alt.Chart(rows.assign(line=data.STORE))
        .mark_line(strokeWidth=2.5, point=True)
        .encode(
            x=x,
            y=alt.Y("recent_price:Q", title=None, scale=scale, axis=axis),
            # The store's ink: the theme's second chart colour.
            color=alt.Color(
                "line:N",
                scale=alt.Scale(domain=[data.FARM, data.STORE]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("recent_month:T", format="%B %Y", title="Month"),
                alt.Tooltip("recent_price:Q", format=",.2f", title=f"₱ per {unit}"),
                alt.Tooltip("usual_low:Q", format=",.2f", title="Usual from"),
                alt.Tooltip("usual_high:Q", format=",.2f", title="Usual to"),
            ],
        )
    )
    return (band + line).properties(height=240)


def season_section(baseline: pd.DataFrame, staple: str) -> None:
    """Is this month's store price usual for the time of year? Nothing for a food
    the mart has no band for."""
    sentence = data.season_sentence(baseline, staple)
    if sentence is None:
        return
    st.subheader(
        "Usual for the time of year?",
        anchor=False,
        help="The usual range is past years' store price for that month, leaving "
        "out the highest and lowest year, scaled to the past 12 months' prices.\n"
        "- Needs at least 5 full past years.\n"
        "- National average.",
    )
    st.markdown(sentence)
    rows = data.usual_year(baseline, staple)
    if rows.empty or float(rows["swing"].iloc[0]) < data.MIN_SEASON_SWING:
        return
    st.caption(
        "The shaded band is the usual price for each month; the line is the store "
        "price over the past 12 months."
    )
    st.altair_chart(
        usual_year_chart(rows, str(rows["unit"].iloc[0])),
        width="stretch",
        alt=f"{staple}: store price over the past 12 months against the usual "
        "range for each month",
    )


def moved(change: float) -> str:
    """A change in words: "rose 24%", "fell 19%", "stayed flat"."""
    if round(change * 100) == 0:
        return "stayed flat"
    return f"{'rose' if change > 0 else 'fell'} {abs(change):.0%}"


def receipt_table(receipt: pd.DataFrame, example: bool) -> None:
    """A basket as a receipt: one line per food in whole pesos, then the total,
    captioned with its months (fish's is a quarter). `example` says whether it is
    still the example basket or the reader's own."""
    if receipt.empty:
        st.caption("Pick a food to see its receipt.")
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
        f":material/receipt_long: {'An example' if example else 'Your'} basket, at "
        f"national prices for {usual}{f' ({others})' if others else ''}."
    )


def cite(fact: context.Fact) -> str:
    """A hand-written fact's source and year, linked, to follow its sentence."""
    return f":gray[([{fact.source}, {fact.date[:4]}]({fact.url}))]"


def so_what(text: str) -> None:
    """The line under a chart that says why it matters."""
    st.markdown(f":material/lightbulb: {text}")


def suspects() -> pd.DataFrame:
    """The public record about the middle (suspects.csv), rulings first."""
    claims = data.load_suspects()
    return claims[claims["role"] == "suspect"]


def fined(claims: pd.DataFrame) -> tuple[str, pd.Timestamp] | None:
    """The record's fines so far, in words ("₱1.76 billion"), and the latest
    fine's date; None before any fine."""
    fines = claims.dropna(subset=["fine_php"])
    if fines.empty:
        return None
    return f"₱{fines['fine_php'].sum() / 1e9:.2f} billion", fines["source_date"].max()


def record_section() -> None:
    """6. Who got caught: the public record about the middle, rulings first (the
    seed's order), each worded as its source words it, with its status and
    source. Context, so text only."""
    claims = suspects()
    st.space("large")
    chapter("caught", "Who got caught")
    fine = fined(claims)
    if fine:
        total, latest = fine
        hero("record", (f"Fined so far, {latest:%b %Y}", total, "middle"))
    st.header("Who got caught", anchor=False)
    st.markdown(
        "Our prices show where the pesos go, not who takes them. This is what "
        "regulators, investigators and lawmakers found, charged or alleged."
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
    chapter("caught", "What can be done")
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
    # Cards, not a bulleted list, so the record's long lines don't read as a
    # paragraph to skip (spec: Word budget).
    for column, fact in zip(
        st.columns(len(context.REPORT)), context.REPORT, strict=True
    ):
        with column.container(border=True, height="stretch"):
            st.markdown(f"{fact.text} {cite(fact)}")


def masthead(shares: pd.DataFrame, growth: pd.DataFrame) -> None:
    """The caption row atop every page: place, food count, the newest PSA
    release's month, and the light/dark button."""
    month = pd.Timestamp(shares["month"].max())
    with st.container(
        horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"
    ):
        # No sentence starts with a numeral, so the count follows the place.
        st.caption(
            f"Philippines · {len(growth)} everyday foods · Updated with PSA's "
            f"{month:%B %Y} release"
        )
        theme.theme_button()


def latest_release(shares: pd.DataFrame) -> pd.Timestamp:
    """When PSA last released a farm, wholesale or store price."""
    columns = ["farmgate_released_at", "retail_released_at", "wholesale_released_at"]
    return pd.Timestamp(shares[columns].max().max())


def footer(
    name: str,
    shares: pd.DataFrame,
    sources: tuple[tuple[str, context.Fact], ...] = (),
) -> None:
    """The foot of every page: the link to the next page, the page's cited
    facts in a closed "Sources" expander (if it has any), then PSA's caption.
    Medium, not large: page 1 ends on a one-line subheader, where a large space
    reads as a hole."""
    st.space("medium")
    st.page_link(nav.page(nav.after(name)), label=f"{NEXT[name]} →")
    if sources:
        with st.expander("Sources", icon=":material/menu_book:"):
            st.markdown(
                "\n".join(f"- {lead}{fact.text} {cite(fact)}" for lead, fact in sources)
            )
    st.divider()
    st.caption(
        f"Farm, wholesale and store prices: PSA OpenSTAT, latest release "
        f"{latest_release(shares):%d %b %Y}. Inflation and diesel: PSA consumer "
        "price index (2018 = 100)."
    )


def story_page() -> None:
    """Page 1, the story: the hook, the chain, the receipt, it's growing, the
    ratchet, then the fines so far, leading on to who got caught."""
    if "food" in st.query_params:
        # A link shared before the pages split: /?food=… opens the food page.
        st.switch_page(nav.page("food"), query_params={"food": st.query_params["food"]})
    shares = data.load(data.SHARES)
    verdicts = data.load(data.VERDICTS)
    growth = data.outran(data.load(data.GROWTH))
    rows = data.farmer_shares(shares)
    masthead(shares, growth)
    st.title("Who's eating the farmer's peso?", anchor=False)
    st.page_link(nav.page("short"), label="Short on time? Read the short version →")
    hook_section(shares)
    chain_section()
    peso_section(shares, rows)
    growing_section(verdicts)
    ratchet_section(verdicts)
    # The ending: the fines so far, then the link on to the record.
    fine = fined(suspects())
    if fine:
        st.space("large")
        st.subheader(
            f"Regulators have fined {paint(fine[0], 'middle')} so far", anchor=False
        )
    footer("story", shares, STORY_SOURCES)


def caught_page() -> None:
    """Page 2, who got caught: the proof that it's every food and not new, the
    public record, then what can be done."""
    shares = data.load(data.SHARES)
    growth = data.outran(data.load(data.GROWTH))
    masthead(shares, growth)
    proof_section(data.farmer_shares(shares), growth)
    record_section()
    remedy_section()
    footer("caught", shares)


def food_page() -> None:
    """Page 3, check your food: one food's prices and numbers."""
    shares = data.load(data.SHARES)
    verdicts = data.load(data.VERDICTS)
    changes = data.load(data.CHANGES)
    change_only = data.load(data.CHANGE_ONLY)
    growth = data.outran(data.load(data.GROWTH))
    rows = data.farmer_shares(shares)
    typical = data.whole_centavos(data.typical_peso(rows)[0])[data.FARMER]
    moves = data.up_and_down(verdicts)
    masthead(shares, growth)
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
    season_section(data.load(data.SEASONAL), staple)
    footer("food", shares)


def short_bullets(
    numbers: dict[str, Any], fine: str | None, move: pd.Series | None
) -> list[str]:
    """The short version, one bullet per finding in the story's order: a bold
    finding with at most one number (a share as pesos of every ₱100), then its
    plain "so what". Every number comes from `data.short_version`, `fined` and
    `data.newest_move`, so the bullets follow each release like the headlines."""
    n = numbers
    gap = n["hook_store"] - n["hook_farm"]
    bullets = [
        (
            f"In {n['hook_month']:%B %Y}, stores charged ₱{gap} a kilo more for "
            "onions than farmers got.",
            "So most of what you paid never reached the person who grew them."
            if n["hook_farmer"] < 50
            else "So the gap between farm and store, not the farmer, set your price.",
        ),
        (
            "Between the farmer and you stand traders, wholesalers and stores.",
            "So your peso is split before any of it reaches the farm, and some of "
            "the split pays for real costs: trucking, storage and spoilage.",
        ),
        (
            f"Farmers get ₱{n['farmer']} of every ₱100 you pay.",
            "So most of your money feeds the traders and stores between the farm "
            "and you, not the person who grew it."
            if n["farmer"] < 50
            else "So the farmer gets most of your money, but not by much.",
        ),
        (
            f"Traders take ₱{n['traders_now'] - n['traders_then']} more of every "
            "₱100 than in 2018.",
            "So the part of your money that misses the farmer is growing.",
        )
        if n["traders_now"] > n["traders_then"]
        else (
            "Traders take no more of every ₱100 than in 2018.",
            "So the middle's part isn't growing, but the farmer's isn't either.",
        ),
        (
            f"When the farm price drops ₱10, you save only ₱{n['drop_save']}.",
            "So when farmers are paid less, you don't get all of it back: the rest "
            "stays in the middle.",
        )
        if n["drop_save"] < 10
        else (
            "When the farm price drops ₱10, you save the whole ₱10.",
            "So falling farm prices do reach you.",
        ),
        (
            f"It's not just onions: farmers get under half for {n['under_half']} "
            f"of {n['shared']} foods.",
            "So it's how your whole basket is priced, not one bad harvest.",
        ),
        (
            f"It's not new: since 2018, store prices grew faster than farm prices "
            f"for {n['outran']} of {n['foods']} foods.",
            "So this has been building for years, not one bad season.",
        ),
    ]
    if fine:
        bullets.append(
            (
                f"Regulators have fined firms in the middle {fine} so far.",
                "So some of the gap isn't costs: the competition regulator ruled "
                "that onion traders and importers divided up the trade.",
            )
        )
    if move is not None:
        went = "rose" if move["now"] > move["before"] else "fell"
        bullets.append(
            (
                f"In {move['month']:%B %Y}, {str(move['staple']).lower()} farmers' "
                f"part {went} to ₱{move['now']} of every ₱100.",
                "So the split moves month to month, and this page follows each PSA "
                "release.",
            )
        )
    bullets.append((context.SABOTAGE.text, "So a cartel in your food is a crime."))
    return [f"**{finding}** {meaning}" for finding, meaning in bullets]


def short_page() -> None:
    """Page 4, the short version: the whole finding as plain bullets, no charts,
    then the way to the proof and to the reader's own food."""
    shares = data.load(data.SHARES)
    verdicts = data.load(data.VERDICTS)
    growth = data.outran(data.load(data.GROWTH))
    masthead(shares, growth)
    st.caption("TL;DR")
    st.title("The short version", anchor=False)
    fine = fined(suspects())
    bullets = short_bullets(
        data.short_version(shares, verdicts, growth),
        fine[0] if fine else None,
        data.newest_move(shares),
    )
    st.markdown("\n".join(f"- {bullet}" for bullet in bullets))
    st.space("small")
    st.page_link(nav.page("story"), label="Want the proof? Read the full story →")
    st.page_link(nav.page("food"), label="Check your own food →")
    footer("short", shares)


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
    chapter("story", "The onion question")
    guess = st.session_state.get(HOOK_GUESS)
    if guess is None:
        # The reader guesses the store price before seeing it (spec: Engagement).
        # No big number yet, and the slider starts at ₱0, so ₱65 shows once.
        st.header(
            f"{farmers_got} What do you think stores charged?",
            help=help_text,
            anchor=False,
        )
        st.markdown(context.ONION_VS_MEAT.text)
        st.slider(
            "Drag to guess",
            min_value=0,
            max_value=math.ceil(2 * store / 50) * 50,
            value=0,
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
        f"Your guess was ₱{guess}"
        + (f", ₱{abs(off)} {'short' if off > 0 else 'over'}." if off else ", spot on.")
        + " The :orange[**shaded gap**] is what traders and stores kept."
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
    chapter("story", "Who's in between")
    st.header(
        "Between the farmer and you: traders, wholesalers and stores",
        help=CHAIN_HELP,
        anchor=False,
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
            st.markdown(fact.text)
    so_what(
        "So who keeps the gap matters: farmers and fisherfolk are among the "
        "poorest Filipinos."
    )


def peso_section(shares: pd.DataFrame, rows: pd.DataFrame) -> None:
    """3. Your peso: the typical peso as a big number, then the example
    receipt."""
    peso, averaged = data.typical_peso(rows)
    typical = data.whole_centavos(peso)[data.FARMER]
    st.space("large")
    chapter("story", "Where your peso goes")
    # Traders' part is section 4's number alone: this one (the latest month's
    # average) differs from its (the last 12 months' median) by a centavo or so.
    hero("peso", ("The farmer's part of a peso", f"{typical}¢", "farm"))
    st.header(
        f"Farmers get :blue[{typical} centavos] of your peso",
        help=SHARE_HELP.format(foods=averaged),
        anchor=False,
    )
    st.markdown(
        "Pick what you buy in a week. The receipt splits it between the "
        ":blue[**farmer**], :orange[**traders**] and stores."
    )
    choices = {
        item: (staple, item, qty) for staple, item, qty in data.basket_choices(shares)
    }
    example = [item for _, item, _ in data.BASKET if item in choices]
    picked = st.multiselect(
        "Your basket",
        list(choices),
        default=example,
        key="basket",
        placeholder="Pick a food",
        label_visibility="collapsed",
    )
    receipt = data.receipt(shares, [choices[item] for item in picked])
    receipt_table(receipt, example=picked == example)
    if receipt.empty:
        return
    total = receipt.iloc[-1]
    after = int(total["traders"] + total["stores"])
    # A week's basket, so a month is 52 weeks over 12.
    so_what(
        f"So of the ₱{total['pay']:,.0f} you pay, ₱{after:,} is spent after the "
        f"farm. Bought every week, that's about ₱{after * 52 / 12:,.0f} a month."
    )


def growing_section(verdicts: pd.DataFrame) -> None:
    """4. It's growing: traders' part of a peso in 2018 against now, as big
    numbers and a headline, no chart."""
    parts = data.parts_then_now(verdicts)
    then, now = round(parts["trader_part_then"]), round(parts["trader_part_now"])
    first = verdicts.iloc[0]
    st.space("large")
    chapter("story", "The middle's growing part")
    hero(
        "middle",
        ("Traders' part of a peso, 2018", f"{then}¢", "plain"),
        ("Now", f"{now}¢", "middle"),
    )
    st.header(
        # Short, so its (?) stays on the headline's last line at phone width;
        # section 3's headline has just said "of your peso".
        f"Traders now take :orange[{now} centavos], up from {then}"
        if now > then
        else f"Traders take :orange[{now} centavos], as in 2018"
        if now == then
        else f"Traders take :orange[{now} centavos], down from {then}",
        help=MIDDLE_HELP.format(
            diesel=pct(first["diesel_change"]),
            transport=pct(first["transport_change"]),
        ),
        anchor=False,
    )
    # No chart here, so the so-what closes the section and it doesn't read as a
    # hole before section 5.
    so_what(
        "So more of every peso you pay now stops with the traders."
        if now > then
        else "So traders' part hasn't grown since 2018."
        if now == then
        else "So traders keep less of every peso than in 2018."
    )


def proof_section(rows: pd.DataFrame, growth: pd.DataFrame) -> None:
    """Who got caught, first: it's not one food (each food's farmer centavos)
    and it's not new (each food's farm and store growth since 2018)."""
    low = rows.iloc[0]
    peso, _ = data.typical_peso(rows)
    chapter("caught", "Every food")
    st.header("It's not one food, and it's not new", anchor=False)
    st.space("small")
    st.subheader(
        f"{low['staple']} farmers get only :blue[{low['farmer']:.0f} centavos] of "
        "your peso",
        anchor=False,
    )
    st.markdown(
        "Each food's :blue[**farmer**] part, lowest first. The dashed line is the "
        "typical food's."
    )
    with reveal("dots"):
        st.echarts_chart(
            farmer_dots(rows, peso[data.FARMER]),
            height=24 * len(rows) + 40,
            key="farmer_dots",
            alt=f"Each food's farmer centavos of every peso, from "
            f"{low['staple'].lower()} at {low['farmer']:.0f} up",
        )
    under = int((rows["farmer"] < 50).sum())
    so_what(
        f"So for {under} of {len(rows)} foods, farmers get less than half of what "
        "you pay."
    )
    ahead = int(growth["outran"].sum())
    st.space("small")
    chapter("caught", "Not new")
    st.subheader(
        f"Since 2018, store prices outran farm prices for :orange[{ahead} of "
        f"{len(growth)} foods]",
        anchor=False,
    )
    st.markdown(
        "Each row joins a food's :blue[**farm**] and **store** growth since 2018; "
        "an :orange[**amber**] line means the store grew faster."
    )
    with reveal("middle"):
        st.echarts_chart(
            middle_chart(growth),
            height=36 * len(growth) + 40,
            key="middle_chart",
            alt="Each food's farm and store price growth since 2018, joined by a "
            "line, the store's biggest lead first",
        )
    so_what("So the difference went to the middle, not the farmer.")


def ratchet_section(verdicts: pd.DataFrame) -> None:
    """5. The ratchet: up fast, down slow, drawn as an example of the typical
    food's moves."""
    moves = data.up_and_down(verdicts)
    slower = int((moves["down"] < moves["up"]).sum())
    up, down = float(moves["up"].median()), float(moves["down"].median())
    most = "Most foods" if slower > len(moves) / 2 else "Some foods"
    # Section 4 has no chart, so a large space here would read as a hole.
    st.space("medium")
    chapter("story", "Up fast, down slow")
    hero("ratchet", ("Of a ₱10 farm drop, you see", f"₱{down:.0f}", "plain"))
    st.header(
        f"Drop ₱10 at the farm, and you save only ₱{down:.0f}"
        if round(down) < 10
        else "Drop ₱10 at the farm, and you save the whole ₱10",
        help=MOVES_HELP.format(up=up, most=most, slower=slower, foods=len(moves)),
        anchor=False,
    )
    st.markdown(
        "The typical food's :blue[**farm price**] goes ₱10 up and back down three "
        "times, and the **store price** follows. The :orange[**bracket**] is what "
        "you pay extra."
    )
    st.caption(":material/science: An example, not a record: the typical food's moves.")
    with reveal("ratchet"):
        st.echarts_chart(
            ratchet_chart(up, down, list(RATCHET_MOVES)),
            height=240,
            key="ratchet_chart",
            alt=f"An example: each move takes the farm price ₱10 up or down; the "
            f"store price rises ₱{up:.0f} and falls ₱{down:.0f} each time",
        )
    extra = sum(round(up) if m > 0 else -round(down) for m in RATCHET_MOVES)
    so_what(
        f"So the farm price is back where it started, but the store price is "
        f"₱{extra} higher. You pay ₱{extra} the farmer never saw."
        if extra > 0
        else "So here the store price kept pace with the farm price both ways."
    )


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
