import streamlit as st
import sys
import os
import pandas as pd
from dotenv import load_dotenv

# Load environment variables for S3 access
load_dotenv()

# Ensure root is in path to find components
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Add src parent dir so we can import 'src'
# The goal is for `import src` to work
# If script is in D:/.../src/dashboard/pages
# dirname = .../pages
# .. = .../dashboard
# ../.. = .../src
# ../../.. = .../ (project root)
# then from src... works
if (
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    not in sys.path
):
    sys.path.append(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    )

from src.dashboard.utils.data_engine import DataEngine  # noqa: E402
from src.dashboard.utils import ui  # noqa: E402
from src.dashboard.components import metrics, spatial  # noqa: E402

# Apply Global Styling
ui.apply_enterprise_styling()


# ==========================================
# PAGE HEADER
# ==========================================
st.markdown(
    """
    <div style="text-align:center; margin-bottom:0.5rem;">
        <h1 style="font-size:2rem; font-weight:700; color:#1e3a5f; margin-bottom:0.1rem;">
            Regional Deep Dive
        </h1>
        <p style="color:#6B7280; font-size:0.9rem; margin-top:0;">Granular Market Intelligence & Regional Price Variance</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# SIDEBAR FILTERS
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
# Ensure the default is valid, otherwise fallback to the most recent date
if default_date_str not in available_dates:
    default_date_str = available_dates[0]

# Date selection via native component
with st.sidebar:
    selected_date = st.date_input(
        "Market Date",
        value=pd.to_datetime(default_date_str).date(),
        min_value=min_data_date,
        max_value=max_data_date,
        help="Select a date to view market prices.",
    )
    # Task 1: Fix Type Mismatch - Explicitly cast to string
    selected_date_str = selected_date.strftime("%Y-%m-%d")

st.session_state["global_date"] = selected_date_str

# Task 2: Unconditional Sidebar Rendering
# Load a reference snapshot for filter population (use latest date if selected is missing)
filter_ref_df = DataEngine.get_market_snapshot(
    selected_date_str if selected_date_str in available_dates else available_dates[0]
)

with st.sidebar:
    if filter_ref_df is not None and not filter_ref_df.empty:
        # 2. Region
        valid_regions = sorted(filter_ref_df["region_name"].dropna().unique())
        default_ix = 0
        if "NCR (NATIONAL CAPITAL REGION)" in valid_regions:
            default_ix = valid_regions.index("NCR (NATIONAL CAPITAL REGION)")
        selected_region = st.selectbox("Region", valid_regions, index=default_ix)

        region_df = filter_ref_df[
            filter_ref_df["region_name"] == selected_region
        ].copy()

        # 3. Category
        valid_categories = sorted(region_df["category"].dropna().unique().tolist())
        default_cat_ix = 0
        for i, cat in enumerate(valid_categories):
            if "RICE" in cat.upper():
                default_cat_ix = i
                break
        selected_category = st.selectbox(
            "Category", valid_categories, index=default_cat_ix
        )

        # 4. Commodity
        cat_df_for_filter = region_df[region_df["category"] == selected_category].copy()
        valid_commods = sorted(cat_df_for_filter["commodity"].dropna().unique())

        default_commod_ix = 0
        if "RICE" in selected_category:
            # Try to find a standard variety for default
            for i, commod in enumerate(valid_commods):
                if "WELL-MILLED" in commod.upper() or "REGULAR" in commod.upper():
                    default_commod_ix = i
                    break

        selected_commodity = st.selectbox(
            "Commodity", valid_commods, index=default_commod_ix
        )
    else:
        st.info("Syncing market metadata...")
        selected_region = None
        selected_category = None
        selected_commodity = None

# Task 3: Correct Execution Flow for Soft-Fail (Main Body)
if selected_date_str not in available_dates:
    st.warning(f"No market data found for {selected_date_str}.")
    st.info(f"Most recent available dates: {', '.join(available_dates[:5])}")
    st.stop()

# UNIFIED SOURCE OF TRUTH (Strictly scoped to Page 1: Regional)
truth_df = DataEngine.get_truth_df(
    selected_date_str,
    region=selected_region,
    category=selected_category,
    commodity=selected_commodity,
)

# LOAD History for trends/deltas
trend_df = DataEngine.get_historical_trends(
    selected_commodity, selected_region, days_back=30, end_date_str=selected_date_str
)

# LOAD REF for Map
geo_df = DataEngine.load_reference_data()


# ==========================================
# ROW 1: EXECUTIVE BRIEF (Commodity Level)
# ==========================================

st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, #1e3a5f 0%, #2E86AB 100%);
        color: white;
        padding: 0.75rem 1.25rem;
        border-radius: 10px;
        margin-bottom: 0.75rem;
        font-size: 1.1rem;
        font-weight: 600;
        text-align: center;
        box-shadow: 0 2px 8px rgba(46, 134, 171, 0.3);
    ">
        Executive Brief: {selected_commodity}
    </div>
    """,
    unsafe_allow_html=True,
)

# Sparkline (Trend)
# Sparkline (Trend) - Fetch 7-Day History
# Previously we tried to derive this from the snapshot, but that only has 1 date.
# We must explicitly fetch history for this specific commodity/region.
trend_df = DataEngine.get_historical_trends(
    selected_commodity, selected_region, days_back=30, end_date_str=selected_date
)

# FIX: Passed commodity_df instead of category_df per user request
# NEW: Pass trend_df to enable Delta calculation
metrics.render_kpi_cards(truth_df, trend_df)

with st.container(border=True):
    metrics.render_sparklines(trend_df, selected_commodity, selected_region)

# Insight derived from unified data (Trend + Truth)
metrics.render_regional_insight(trend_df, selected_commodity, truth_df=truth_df)

# ==========================================
# EXECUTIVE SUMMARY
# ==========================================
# (Removed per user instruction)


# ==========================================
# ROW 1.5: REGIONAL CONTEXT (New Feature)
# ==========================================

# Remove top-level header to put it inside the card for alignment
# st.subheader(f"Regional Price Comparison: {selected_commodity}")

# Advanced Market Leaderboard
with st.container(border=True):
    st.caption(
        "Reading Guide: Markets ranked from cheapest (top) to most expensive (bottom)."
    )
    metrics.render_market_leaderboard(truth_df, selected_commodity)

# LOAD Substitutes for the category analytics
substitutes_df = DataEngine.get_truth_df(
    selected_date_str, region=selected_region, category=selected_category
)

# ==========================================
# ROW 2: VISUAL INTELLIGENCE (Final Production Quadrant)
# ==========================================

top_l, top_r = st.columns(2)
with top_l:
    with st.container(border=True):
        st.markdown("### Market Locations")
        st.caption("Geography: Larger markers indicate price intensity.")
        geo_enriched = DataEngine.enrich_with_geo(truth_df.copy(), geo_df)
        spatial.render_market_map(geo_enriched)

with top_r:
    with st.container(border=True):
        metrics.render_category_substitutes(substitutes_df, selected_commodity)

bot_l, bot_r = st.columns(2)
with bot_l:
    with st.container(border=True):
        metrics.render_historical_baseline_delta(truth_df, trend_df)

with bot_r:
    with st.container(border=True):
        st.markdown("### Price Fairness Index")
        st.caption("Index: Market-level deviation from the regional average.")
        metrics.render_zscore_chart(truth_df)


# ==========================================
# ROW 3: THE LEDGER
# ==========================================

st.subheader("Official Price Bulletin")

# Format for display
display_df = (
    truth_df[["market_name", "commodity", "Prevailing Price (₱)", "days_ago"]]
    .copy()
    .sort_values("Prevailing Price (₱)")
    .reset_index(drop=True)
)
# Pre-format Price as string to force Left Alignment in st.dataframe
display_df["Price"] = display_df["Prevailing Price (₱)"].map("₱{:,.2f}".format)

display_df["Freshness"] = display_df["days_ago"].apply(
    lambda x: "Today" if x == 0 else f"{x} days ago"
)


# Apply Alternating Colors to Bulletin
def alternating_rows(row):
    color = "#F0F2F6" if row.name % 2 != 0 else "#FAFAFA"
    return ["background-color: {}".format(color) for _ in row]


st.dataframe(
    display_df.style.apply(alternating_rows, axis=1),
    column_config={
        "market_name": "Market",
        "Price": st.column_config.TextColumn("Price"),
        "Prevailing Price (₱)": None,  # Hide original numeric
        "days_ago": None,  # Hide raw
    },
    width="stretch",
    hide_index=True,
)


st.caption(
    "Data Source: [Department of Agriculture - Bantay Presyo](http://www.bantaypresyo.da.gov.ph/) | © 2026 Agri-Price Intelligence Platform"
)
