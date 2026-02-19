import streamlit as st
import sys
import os
import pandas as pd
import altair as alt
from dotenv import load_dotenv

# Load environment variables for S3 access
load_dotenv()

# Ensure root is in path
if (
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    not in sys.path
):
    sys.path.append(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    )

from src.dashboard.utils.data_engine import DataEngine  # noqa: E402
from src.dashboard.utils import ui  # noqa: E402
from src.dashboard.components import metrics  # noqa: E402

# Apply Global Styling
ui.apply_enterprise_styling()


# ==========================================
# PAGE HEADER
# ==========================================
st.markdown(
    """
    <div style="text-align:center; margin-bottom:0.5rem;">
        <h1 style="font-size:2rem; font-weight:700; color:#1e3a5f; margin-bottom:0.1rem;">
            Strategic Analysis: Historical Trends
        </h1>
        <p style="color:#6B7280; font-size:0.9rem; margin-top:0;">Long-Term Price Trajectory &amp; Volatility</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# CONFIGURATION & FILTERS
# ==========================================
st.sidebar.header("Configuration")

# 1. Date Range
range_options = {
    "Last 7 Days": 7,
    "Last 30 Days": 30,
    "Last 90 Days": 90,
    "Year to Date": 365,
}
selected_range_label = st.sidebar.selectbox(
    "Time Horizon", list(range_options.keys()), index=1
)
days_back = range_options[selected_range_label]

# 2. Region & Commodity Selection
# Initialize DataEngine to retrieve the latest available dataset date
min_date, max_date = DataEngine.get_date_range()
if not max_date:
    st.warning("No data currently available. Please check back later.")
    st.info(
        "The ETL pipeline runs daily. Data may be temporarily unavailable during processing."
    )
    st.stop()

latest_date = max_date.strftime("%Y-%m-%d")
reference_df = DataEngine.get_market_snapshot(latest_date)

if reference_df is None or reference_df.empty:
    st.warning(f"Unable to load data for {latest_date}.")
    st.info("Try again later or contact support if the issue persists.")
    st.stop()

# Region Selection
valid_regions = sorted(reference_df["region_name"].dropna().unique())
default_ix = 0
if "NCR (NATIONAL CAPITAL REGION)" in valid_regions:
    default_ix = valid_regions.index("NCR (NATIONAL CAPITAL REGION)")
selected_region = st.sidebar.selectbox("Region", valid_regions, index=default_ix)

# Commodity Selection (Filtered by Region)
region_ref_df = reference_df[reference_df["region_name"] == selected_region]
valid_commodities = sorted(region_ref_df["commodity"].dropna().unique())
selected_commodity = st.sidebar.selectbox("Commodity", valid_commodities)


# ==========================================
# DATA INGESTION
# ==========================================
with st.spinner(f"Loading {days_back} days of history for {selected_commodity}..."):
    hist_df = DataEngine.get_historical_trends(
        selected_commodity, selected_region, days_back=days_back
    )

if hist_df.empty:
    st.warning(
        f"No historical data found for {selected_commodity} in {selected_region} over the last {days_back} days."
    )
    st.stop()

# ==========================================
# VISUALIZATION
# ==========================================

# METRICS SUMMARY
avg_price_period = hist_df["Prevailing Price (₱)"].mean()
min_price_period = hist_df["Prevailing Price (₱)"].min()
max_price_period = hist_df["Prevailing Price (₱)"].max()

# Fetch the prior equivalent period to compute meaningful deltas.
# E.g. for 'Last 30 Days', fetch the 60 days before today and take the
# first 30 days as the baseline. Falls back gracefully if no prior data.
prior_df = DataEngine.get_historical_trends(
    selected_commodity, selected_region, days_back=days_back * 2
)
# Isolate only the older half (the prior period).
if not prior_df.empty:
    cutoff = prior_df["extract_dt"].max() - pd.Timedelta(days=days_back)
    prior_window = prior_df[prior_df["extract_dt"] <= cutoff]
    avg_prior = (
        prior_window["Prevailing Price (₱)"].mean() if not prior_window.empty else None
    )
else:
    avg_prior = None

# Delta for Period Average: % change vs prior period.
if avg_prior and avg_prior != 0:
    avg_delta_pct = ((avg_price_period - avg_prior) / avg_prior) * 100
    avg_delta_str = f"{avg_delta_pct:+.1f}% vs prior {days_back}d"
else:
    avg_delta_str = None

# Delta for Period Low: deviation below the period average (always negative or zero).
low_delta_pct = (
    ((min_price_period - avg_price_period) / avg_price_period) * 100
    if avg_price_period
    else None
)
low_delta_str = f"{low_delta_pct:+.1f}% vs avg" if low_delta_pct is not None else None

# Delta for Period High: deviation above the period average (always positive or zero).
high_delta_pct = (
    ((max_price_period - avg_price_period) / avg_price_period) * 100
    if avg_price_period
    else None
)
high_delta_str = (
    f"{high_delta_pct:+.1f}% vs avg" if high_delta_pct is not None else None
)

m1, m2, m3 = st.columns(3)
with m1:
    with st.container(border=True):
        st.metric(
            "Period Average",
            f"₱{avg_price_period:,.2f}",
            delta=avg_delta_str,
            delta_color="inverse",  # Red = price up (bad), green = price down (good).
        )
with m2:
    with st.container(border=True):
        st.metric(
            "Period Low",
            f"₱{min_price_period:,.2f}",
            delta=low_delta_str,
            delta_color="inverse",
        )
with m3:
    with st.container(border=True):
        st.metric(
            "Period High",
            f"₱{max_price_period:,.2f}",
            delta=high_delta_str,
            delta_color="inverse",
        )

# Historical insight: price spread over the period + best day of week to buy.
metrics.render_historical_insight(hist_df, selected_commodity)

# ==========================================
# 30-DAY MARKET BRIEFING
# ==========================================

# Identify the dates of the extreme prices for the narrative.
_max_price_row = hist_df.loc[hist_df["Prevailing Price (₱)"].idxmax()]
_min_price_row = hist_df.loc[hist_df["Prevailing Price (₱)"].idxmin()]
_max_price_date = _max_price_row["extract_dt"].strftime("%b %d, %Y")
_min_price_date = _min_price_row["extract_dt"].strftime("%b %d, %Y")
_volatility = max_price_period - min_price_period

with st.expander("30-Day Market Briefing", expanded=True):
    st.markdown(
        f"""
        Over the selected **{days_back}-day** window, **{selected_commodity}** in **{selected_region}** \
averaged **₱{avg_price_period:,.2f}**. \
The highest recorded price was **₱{max_price_period:,.2f}** on **{_max_price_date}**, \
while the lowest was **₱{min_price_period:,.2f}** on **{_min_price_date}**. \
The overall price spread (volatility) for this period is **₱{_volatility:,.2f}**—\
{'indicating a stable market with minimal price fluctuation.' if _volatility < 20 else 'suggesting notable price volatility across the period.'}
        """
    )

with st.container(border=True):
    st.markdown("#### Price Trajectory by Market")
    st.caption("Tracking daily price movements across different markets in the region.")

    with st.expander("How to Read This Chart", expanded=False):
        st.markdown(
            """
        *   **Upward Slope**: Prices are getting more expensive (Inflation).
        *   **Downward Slope**: Prices are going down (Supply is stabilizing).
        *   **High Flyers**: Lines far above the rest may indicate localized shortages.
        *   **Tight Cluster**: When lines are close together, prices are consistent across markets.
        """
        )

    # Line Chart: X=Date, Y=Price, Color=Market
    # Visualization configured for enterprise clarity with interactive tooltips and distinct color schemes
    line_chart = (
        alt.Chart(hist_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("extract_dt:T", title="Date", axis=alt.Axis(format="%b %d")),
            y=alt.Y(
                "Prevailing Price (₱):Q", title="Price (₱)", scale=alt.Scale(zero=False)
            ),
            color=alt.Color(
                "market_name:N", title="Market", scale=alt.Scale(scheme="tableau20")
            ),
            tooltip=[
                alt.Tooltip("extract_dt", title="Date", format="%b %d, %Y"),
                alt.Tooltip("market_name", title="Market"),
                alt.Tooltip("Prevailing Price (₱)", title="Price", format=",.2f"),
            ],
        )
        .properties(height=400)
        .configure_axis(grid=False)
        .interactive()
    )

    st.altair_chart(line_chart, use_container_width=True)

# CHART 2: VOLATILITY / SPREAD
with st.container(border=True):
    st.markdown("#### Daily Price Spread (Volatility)")
    st.caption("The gap between the cheapest and most expensive market each day.")

    # Calculate Daily Min/Max/Avg
    daily_stats = (
        hist_df.groupby("extract_dt")["Prevailing Price (₱)"]
        .agg(["min", "max", "mean"])
        .reset_index()
    )
    daily_stats["spread"] = daily_stats["max"] - daily_stats["min"]

    # Area Chart for Price Range (Min-Max)
    base = alt.Chart(daily_stats).encode(x=alt.X("extract_dt:T", title="Date"))

    # Render Range Area (Slate Blue)
    area = base.mark_area(opacity=0.3, color="#2E86AB").encode(
        y=alt.Y("min:Q", title="Price Range (₱)", scale=alt.Scale(zero=False)),
        y2="max:Q",
        tooltip=[
            alt.Tooltip("extract_dt", title="Date", format="%b %d, %Y"),
            alt.Tooltip("min", title="Min Price", format=",.2f"),
            alt.Tooltip("max", title="Max Price", format=",.2f"),
            alt.Tooltip("mean", title="Avg Price", format=",.2f"),
        ],
    )

    # Render Average Line (Muted Coral, Dashed)
    line_avg = base.mark_line(color="#D64045", strokeDash=[5, 5]).encode(y="mean:Q")

    combined = (
        (area + line_avg)
        .properties(height=300)
        .configure_axis(grid=False)
        .interactive()
    )

    st.altair_chart(combined, use_container_width=True)
    st.caption(
        "Blue Area = Price Range (Low to High). Red Dashed Line = Market Average."
    )

# CHART 3: BEST DAY TO BUY (Day of Week Analysis)
with st.container(border=True):
    st.markdown("#### Best Day to Buy Analysis")
    st.caption(
        "Which day of the week typically offers the lowest prices? Based on historical averages."
    )

    # Prepare Data
    if "extract_dt" in hist_df.columns and not hist_df.empty:
        dow_df = hist_df.copy()
        dow_df["day_name"] = dow_df["extract_dt"].dt.day_name()

        # Aggregate
        dow_stats = (
            dow_df.groupby("day_name")["Prevailing Price (₱)"].mean().reset_index()
        )
        # Sort by Price (Cheapest first) for the chart
        dow_stats = dow_stats.sort_values("Prevailing Price (₱)")

        # Highlight the BEST day (First row after sort)
        if not dow_stats.empty:
            best_day = dow_stats.iloc[0]["day_name"]
            dow_stats["is_best"] = dow_stats["day_name"] == best_day

            # Bar Chart: X=Price, Y=Day, Color=Best Day Highlight
            base = alt.Chart(dow_stats).encode(
                x=alt.X("Prevailing Price (₱):Q", title="Avg Price (₱)"),
                y=alt.Y(
                    "day_name:N",
                    sort=alt.EncodingSortField(
                        field="Prevailing Price (₱)", order="ascending"
                    ),
                    title=None,
                ),
                tooltip=[
                    alt.Tooltip("day_name", title="Day"),
                    alt.Tooltip(
                        "Prevailing Price (₱)", title="Avg Price", format=",.2f"
                    ),
                ],
            )

            bars = base.mark_bar().encode(
                color=alt.condition(
                    alt.datum.day_name == best_day,
                    alt.value(
                        "#2ca02c"
                    ),  # Best day: green (consistent with regional bar chart)
                    alt.value("#d3d3d3"),  # All others: muted gray
                )
            )

            text = base.mark_text(align="left", dx=3, color="#333333").encode(
                text=alt.Text("Prevailing Price (₱):Q", format=",.0f")
            )

            # Sort descending so the cheapest (green) bar is at the bottom —
            # a natural visual anchor for the 'best deal' reading direction.
            chart = (
                (bars + text)
                .encode(
                    y=alt.Y(
                        "day_name:N",
                        sort=alt.EncodingSortField(
                            field="Prevailing Price (₱)", order="descending"
                        ),
                        title=None,
                    )
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)
            st.success(
                f"**Insight:** Historical data suggests **{best_day}** is generally the best day to buy."
            )

# ==========================================
# FOOTER
# ==========================================

st.caption(
    "Data Source: [Department of Agriculture - Bantay Presyo](http://www.bantaypresyo.da.gov.ph/) | © 2026 Agri-Price Intelligence Platform"
)
