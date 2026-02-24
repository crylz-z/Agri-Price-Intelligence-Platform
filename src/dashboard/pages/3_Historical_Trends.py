# ruff: noqa: E402
import streamlit as st
import sys
import os
import datetime
import pandas as pd
import altair as alt
from dotenv import load_dotenv

# Load environment variables for S3 access
load_dotenv()

# Ensure root is in path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.dashboard.utils.data_engine import DataEngine
from src.dashboard.utils import ui
from src.dashboard.components import metrics

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
        max_value=datetime.date.today(),
        help="Select the end date for historical analysis.",
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

    # Load data for filter population (use Truth for consistency)
    filter_ref_df = DataEngine.get_market_snapshot(
        selected_date_str
        if selected_date_str in available_dates
        else available_dates[0]
    )

    if filter_ref_df is not None and not filter_ref_df.empty:
        # 1. Region Selection
        valid_regions = sorted(filter_ref_df["region_name"].dropna().unique())
        default_ix = 0
        if "NCR (NATIONAL CAPITAL REGION)" in valid_regions:
            default_ix = valid_regions.index("NCR (NATIONAL CAPITAL REGION)")
        selected_region = st.selectbox("Region", valid_regions, index=default_ix)
        region_df_filter = filter_ref_df[
            filter_ref_df["region_name"] == selected_region
        ].copy()

        # 2. Category Selection
        valid_categories = sorted(region_df_filter["category"].dropna().unique())
        default_cat_ix = 0
        for i, cat in enumerate(valid_categories):
            if "RICE" in cat.upper():
                default_cat_ix = i
                break
        selected_category = st.selectbox(
            "Category", valid_categories, index=default_cat_ix
        )
        category_df_filter = region_df_filter[
            region_df_filter["category"] == selected_category
        ].copy()

        # 3. Commodity Selection
        valid_commods = sorted(category_df_filter["commodity"].dropna().unique())
        default_commod_ix = 0
        if "RICE" in selected_category:
            for i, commod in enumerate(valid_commods):
                if "WELL-MILLED" in commod.upper() or "REGULAR" in commod.upper():
                    default_commod_ix = i
                    break
        selected_commodity = st.selectbox(
            "Commodity", valid_commods, index=default_commod_ix
        )
    else:
        st.info("Syncing historical metadata...")
        selected_region = None
        selected_category = None
        selected_commodity = None

# Task 3: Graceful Fallback for Missing Dates
actual_date_str = selected_date_str
if selected_date_str not in available_dates:
    closest_dates = [d for d in available_dates if d < selected_date_str]
    is_today = selected_date_str == datetime.date.today().strftime("%Y-%m-%d")

    if closest_dates:
        actual_date_str = closest_dates[0]
        if is_today:
             st.warning(f"🕒 **Pending Extraction**: Market data for `{selected_date_str}` is not yet available. Falling back to the latest data from `{actual_date_str}`.")
        else:
             st.warning(f"⚠️ **Server Outage Detected**: No market data found for `{selected_date_str}`. Falling back to the last known good data from `{actual_date_str}`.")
    else:
        st.error(f"No market data found for {selected_date_str} and no prior history exists.")
        st.stop()

# DATA INGESTION
with st.spinner(f"Loading {days_back} days of history for {selected_commodity}..."):
    hist_df = DataEngine.get_historical_trends(
        selected_commodity,
        selected_region,
        days_back=days_back,
        end_date_str=actual_date_str,
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

m1, m2, m3 = st.columns(3)
with m1:
    with st.container(border=True):
        st.metric("Period Average", f"₱{avg_price_period:,.2f}")
with m2:
    with st.container(border=True):
        st.metric("Period Low", f"₱{min_price_period:,.2f}")
with m3:
    with st.container(border=True):
        st.metric("Period High", f"₱{max_price_period:,.2f}")

# Historical insight: price spread over the period + best day of week to buy.
metrics.render_historical_period_insight(hist_df, selected_commodity)

# ==========================================
# CHARTS
# ==========================================

# ==========================================
# CHARTS: TEMPORAL ANALYTICS OVERHAUL
# ==========================================

# Data Prep
df_plot = hist_df.copy()
df_plot["price"] = pd.to_numeric(df_plot["Prevailing Price (₱)"], errors="coerce")
df_plot = df_plot.dropna(subset=["price"])

# Task 1: Aggregation Math (Fixing the Barcode Bug)
daily_agg = (
    df_plot.groupby("extract_dt")["price"]
    .agg(min_price="min", max_price="max", mean_price="mean")
    .reset_index()
)

# Task 2: Build the 'Price Volatility Envelope'
with st.container(border=True):
    st.markdown("### Regional Price Volatility (30-Day Envelope)")
    st.caption(
        "Reading Guide: The shaded Slate area represents the spread between the cheapest and most expensive markets. The Teal line represents the regional average."
    )

    envelope = (
        alt.Chart(daily_agg)
        .mark_area(opacity=0.3, color="#64748b")
        .encode(
            x=alt.X("extract_dt:T", title=None, axis=alt.Axis(format="%b %d")),
            y=alt.Y("min_price:Q", title="Price (₱)", scale=alt.Scale(zero=False)),
            y2="max_price:Q",
        )
    )

    average = (
        alt.Chart(daily_agg)
        .mark_line(color="#0d9488", strokeWidth=3)
        .encode(
            x="extract_dt:T",
            y="mean_price:Q",
            tooltip=[
                alt.Tooltip("extract_dt:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("mean_price:Q", title="Avg Price", format=",.2f"),
                alt.Tooltip("min_price:Q", title="Min Price", format=",.2f"),
                alt.Tooltip("max_price:Q", title="Max Price", format=",.2f"),
            ],
        )
    )

    chart_vol = (envelope + average).properties(height=350)
    st.altair_chart(chart_vol, width="stretch", theme=None)

# Task 3: Build the 'Calendar Price Matrix' (Heatmap)
with st.container(border=True):
    st.markdown("### Day-of-Week Price Intensity Matrix")
    st.caption(
        "Reading Guide: Visualizes temporal pricing patterns. Darker Coral squares indicate days with historically higher average prices."
    )

    # Day-of-week sorting
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    # Calculate day and week for the heatmap
    daily_agg["day_of_week"] = daily_agg["extract_dt"].dt.day_name()
    daily_agg["week_of_year"] = daily_agg["extract_dt"].dt.isocalendar().week

    heatmap = (
        alt.Chart(daily_agg)
        .mark_rect(stroke="#ffffff", strokeWidth=2)
        .encode(
            x=alt.X("week_of_year:O", title=None, axis=None),
            y=alt.Y(
                "day_of_week:N",
                sort=days_order,
                title=None,
                scale=alt.Scale(domain=days_order),
            ),
            color=alt.Color(
                "mean_price:Q",
                scale=alt.Scale(range=["#f1f5f9", "#e11d48"]),
                title="Avg Price (₱)",
                legend=alt.Legend(orient="bottom", gradientLength=200),
            ),
            tooltip=[
                alt.Tooltip("extract_dt:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("mean_price:Q", title="Avg Price", format=",.2f"),
                alt.Tooltip("day_of_week:N", title="Day"),
            ],
        )
        .properties(height=300)
    )

    st.altair_chart(heatmap, width="stretch", theme=None)

# Task 4: High-Level Insight (Best Day Comparison)
best_day = daily_agg.groupby("day_of_week")["mean_price"].mean().idxmin()
st.info(
    f"Temporal Analysis: Historical data for this period indicates that **{best_day}** typically offers the most competitive regional pricing."
)

st.caption(
    "Data Source: [Department of Agriculture - Bantay Presyo](http://www.bantaypresyo.da.gov.ph/) | © 2026 Agri-Price Intelligence Platform"
)

ui.render_system_health()
