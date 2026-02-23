import streamlit as st
import sys
import os
import pandas as pd
import altair as alt
from datetime import datetime
from zoneinfo import ZoneInfo
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
st.sidebar.markdown("### Configuration")

available_dates = DataEngine.get_available_dates()
if not available_dates:
    st.error("No data available in S3 Silver layer.")
    st.stop()

# Determine first and last dates in dataset
min_data_date = pd.to_datetime(available_dates[-1]).date()
max_data_date = pd.to_datetime(available_dates[0]).date()

default_date_str = st.session_state.get("global_date")
if default_date_str not in available_dates:
    default_date_str = available_dates[0]

# Date selection via native component in sidebar
with st.sidebar:
    selected_date = st.date_input(
        "End Date",
        value=pd.to_datetime(default_date_str).date(),
        min_value=min_data_date,
        max_value=max_data_date,
        help="Select the end date for historical analysis."
    )
    # Task 1: Fix Type Mismatch
    selected_date_str = selected_date.strftime("%Y-%m-%d")

st.session_state["global_date"] = selected_date_str

# Task 2: Unconditional Sidebar Rendering
with st.sidebar:
    st.markdown("---")
    range_options = {
        "Last 7 Days": 7,
        "Last 30 Days": 30,
        "Last 90 Days": 90,
        "Year to Date": 365,
    }
    selected_range_label = st.selectbox(
        "Time Horizon", list(range_options.keys()), index=1
    )
    days_back = range_options[selected_range_label]

    # Load data for filter population (use latest date if selected is missing)
    filter_ref_df = DataEngine.get_market_snapshot(selected_date_str if selected_date_str in available_dates else available_dates[0])
    
    if filter_ref_df is not None and not filter_ref_df.empty:
        # 2. Region Selection
        valid_regions = sorted(filter_ref_df["region_name"].dropna().unique())
        selected_region = st.selectbox("Region", valid_regions)
        region_df_filter = filter_ref_df[filter_ref_df["region_name"] == selected_region].copy()

        # 3. Category Selection
        valid_categories = sorted(region_df_filter["category"].dropna().unique())
        selected_category = st.selectbox("Category", valid_categories)
        category_df_filter = region_df_filter[region_df_filter["category"] == selected_category].copy()

        # 4. Commodity Selection
        valid_commods = sorted(category_df_filter["commodity"].dropna().unique())
        selected_commodity = st.selectbox("Commodity", valid_commods)
    else:
        st.info("Syncing historical metadata...")
        selected_region = None
        selected_category = None
        selected_commodity = None

# Task 3: Correct Execution Flow for Soft-Fail (Main Body)
if selected_date_str not in available_dates:
    st.warning(f"No market data found for {selected_date_str}.")
    st.info(f"Most recent available dates: {', '.join(available_dates[:5])}")
    st.stop()

# Prepare data for charts
trend_df = DataEngine.get_historical_trends(selected_date_str, days_back)
if trend_df is None or trend_df.empty:
    st.error("Could not retrieve trend data for the selected period.")
    st.stop()

commodity_df = trend_df[
    (trend_df["region_name"] == selected_region) & 
    (trend_df["category"] == selected_category) & 
    (trend_df["commodity"] == selected_commodity)
].copy()

# ==========================================
# DATA INGESTION
# ==========================================
with st.spinner(f"Loading {days_back} days of history for {selected_commodity}..."):
    hist_df = DataEngine.get_historical_trends(
        selected_commodity,
        selected_region,
        days_back=days_back,
        end_date_str=latest_date,
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
    selected_commodity,
    selected_region,
    days_back=days_back * 2,
    end_date_str=latest_date,
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
{"indicating a stable market with minimal price fluctuation." if _volatility < 20 else "suggesting notable price volatility across the period."}
        """
    )

with st.container(border=True):
    st.markdown(
        f"#### Price Trend (Last {days_back} Days) - {selected_commodity} ({selected_region})"
    )
    st.caption(f"📍 Geographic Context: {selected_region}")
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
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("extract_dt:T", title="Date", axis=alt.Axis(format="%b %d")),
            y=alt.Y(
                "Prevailing Price (₱):Q", title="Price (₱)", scale=alt.Scale(zero=False)
            ),
            color=alt.Color(
                "market_name:N", title="Market", scale=alt.Scale(scheme="tealblues")
            ),
            tooltip=[
                alt.Tooltip("extract_dt", title="Date", format="%b %d, %Y"),
                alt.Tooltip("market_name", title="Market"),
                alt.Tooltip("Prevailing Price (₱)", title="Price", format=",.2f"),
            ],
        )
        .properties(height=400)
        .configure_axis(grid=False)
        .configure_view(strokeOpacity=0)
        .interactive()
    )

    st.altair_chart(line_chart, width="stretch", theme=None)

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

    # Render Range Area (Teal)
    area = base.mark_area(opacity=0.3, color="#1f77b4").encode(
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

    st.altair_chart(combined, width="stretch", theme=None)
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
            st.altair_chart(chart, width="stretch")
            st.success(
                f"**Insight:** Historical data suggests **{best_day}** is generally the best day to buy."
            )


st.caption(
    "Data Source: [Department of Agriculture - Bantay Presyo](http://www.bantaypresyo.da.gov.ph/) | © 2026 Agri-Price Intelligence Platform"
)
