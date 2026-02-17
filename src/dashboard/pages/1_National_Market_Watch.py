import streamlit as st
import sys
import os
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

from src.dashboard.utils.data_engine import DataEngine
from src.dashboard.utils import ui
from src.dashboard.components import metrics, spatial

# Apply Global Styling
ui.apply_enterprise_styling()
import altair as alt

st.set_page_config(layout="wide", page_title="National Market Watch", page_icon="🌽")

# ==========================================
# PAGE HEADER
# ==========================================
st.title("National Market Watch")
st.markdown("### Real-Time Price Monitoring & Intelligence")


# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.header("Configuration")

# 1. Date
# 1. Date
min_date, max_date = DataEngine.get_date_range()
if not min_date or not max_date:
    st.warning("⚠️ No data currently available. Please check back later.")
    st.info("The ETL pipeline runs daily. Data may be temporarily unavailable during processing.")
    st.stop()

# Calendar Picker
picked_date = st.sidebar.date_input(
    "Date",
    value=max_date,
    min_value=min_date,
    max_value=max_date,
    help="Select a date to view market prices.",
)
selected_date = picked_date.strftime("%Y-%m-%d")

# LOAD DATA (LKGV)
raw_df = DataEngine.get_market_snapshot(selected_date)
if raw_df is None or raw_df.empty:
    st.warning(f"⚠️ No data available for {selected_date}.")
    st.info("Try selecting a different date or check back later.")
    st.stop()

# 2. Region
valid_regions = sorted(raw_df["region_name"].dropna().unique())
default_ix = 0
if "NCR (NATIONAL CAPITAL REGION)" in valid_regions:
    default_ix = valid_regions.index("NCR (NATIONAL CAPITAL REGION)")

selected_region = st.sidebar.selectbox("Region", valid_regions, index=default_ix)
region_df = raw_df[raw_df["region_name"] == selected_region].copy()

# 3. Category
valid_categories = sorted(region_df["category"].dropna().unique())
selected_category = st.sidebar.selectbox("Category", valid_categories)
category_df = region_df[region_df["category"] == selected_category].copy()

# 4. Commodity
valid_commodities = sorted(category_df["commodity"].dropna().unique())
selected_commodity = st.sidebar.selectbox("Commodity Focus", valid_commodities)
commodity_df = category_df[category_df["commodity"] == selected_commodity].copy()

# LOAD REF
geo_df, srp_df = DataEngine.load_reference_data()


# ==========================================
# ROW 1: EXECUTIVE BRIEF (Commodity Level)
# ==========================================

st.subheader(f"Executive Brief: {selected_commodity}")

# Sparkline (Trend)
# Sparkline (Trend) - Fetch 7-Day History
# Previously we tried to derive this from the snapshot, but that only has 1 date.
# We must explicitly fetch history for this specific commodity/region.
trend_df = DataEngine.get_historical_trends(
    selected_commodity, selected_region, days_back=7
)

# FIX: Passed commodity_df instead of category_df per user request
# NEW: Pass trend_df to enable Delta calculation
metrics.render_kpi_cards(commodity_df, trend_df)

with st.container(border=True):
    metrics.render_sparklines(trend_df, selected_commodity)

# ==========================================

# ==========================================
# ROW 1.5: REGIONAL CONTEXT (New Feature)
# ==========================================

# Remove top-level header to put it inside the card for alignment
# st.subheader(f"Regional Price Comparison: {selected_commodity}")

col_bar, col_top5 = st.columns(2)

with col_bar:
    with st.container(border=True):
        st.markdown(f"#### Regional Comparison: {selected_commodity}")
        # Calculate Average Price per Region for this Commodity (Snapshot)
        # We need to load raw data for ALL regions for this date first.
        # Currently `raw_df` acts as our snapshot.
        # Filter raw_df for the selected commodity across ALL regions
        cross_region_df = raw_df[raw_df["commodity"] == selected_commodity].copy()

        if not cross_region_df.empty:
            reg_stats = (
                cross_region_df.groupby("region_name")["Prevailing Price (₱)"]
                .mean()
                .reset_index()
            )
            reg_stats = reg_stats.sort_values("Prevailing Price (₱)", ascending=False)

            # Highlight current region
            # Enterprise Colors: #2E86AB (Blue) for others, #D64045 (Red) for selected

            chart_reg = (
                alt.Chart(reg_stats)
                .mark_bar()
                .encode(
                    x=alt.X("Prevailing Price (₱):Q", title="Avg Price (₱)"),
                    y=alt.Y("region_name:N", sort="-x", title=None),
                    # Precise Enterprise Color Logic
                    color=alt.condition(
                        alt.datum.region_name == selected_region,
                        alt.value("#D64045"),  # Red highlight for selected
                        alt.value("#2E86AB"),  # Slate Blue for all others
                    ),
                    tooltip=["region_name", "Prevailing Price (₱)"],
                )
                .properties(height=400)
                .configure_axis(grid=False)
            )
            st.altair_chart(chart_reg, use_container_width=True)
        else:
            st.info("No cross-regional data available.")

with col_top5:
    with st.container(border=True):
        st.markdown("#### Top 5 Most Expensive Markets")
        if not cross_region_df.empty:
            top5 = cross_region_df.nlargest(5, "Prevailing Price (₱)")[
                ["region_name", "market_name", "Prevailing Price (₱)"]
            ].reset_index(drop=True)

            # Apply Alternating Colors (Professional Look)
            # Dirty White (#FAFAFA) and Light Gray (#F0F2F6)
            def alternating_rows(row):
                color = "#F0F2F6" if row.name % 2 != 0 else "#FAFAFA"
                return ["background-color: {}".format(color) for _ in row]

            st.dataframe(
                top5.style.apply(alternating_rows, axis=1).format(
                    {"Prevailing Price (₱)": "₱{:.2f}"}
                ),
                column_config={
                    "region_name": "Region",
                    "market_name": "Market",
                    "Prevailing Price (₱)": st.column_config.NumberColumn(
                        "Price", format="₱%.2f"
                    ),
                },
                hide_index=True,
                use_container_width=True,
                height=400,
            )

# ==========================================
# FOOTER
# ==========================================


# ==========================================
# ROW 2: VISUAL INTELLIGENCE
# ==========================================

# 50/50 Split per request
col_map, col_alert = st.columns(2)

with col_map:
    with st.container(border=True):
        st.markdown(f"#### Market Locations")
        # Enhance specific commodity data with Geo
        # This uses the Resilient Geo-Join from Data Engine
        geo_enriched = DataEngine.enrich_with_geo(commodity_df, geo_df)

        # Render Map Feature
        spatial.render_market_map(geo_enriched)
        # st.warning("Map disabled for debugging")

with col_alert:
    with st.container(border=True):
        st.markdown("#### Price Watch")
        # Check for Gouging
        metrics.render_gouging_alert(commodity_df, srp_df)

        # Z-Score Chart (Restored)
        metrics.render_zscore_chart(commodity_df, height=400)


# ==========================================
# ROW 3: THE LEDGER
# ==========================================

st.subheader("Official Price Bulletin")

# Format for display
display_df = (
    commodity_df[["market_name", "commodity", "Prevailing Price (₱)", "days_ago"]]
    .copy()
    .reset_index(drop=True)
)
display_df["Freshness"] = display_df["days_ago"].apply(
    lambda x: "Today" if x == 0 else f"{x} days ago"
)

# Apply Alternating Colors to Bulletin
st.dataframe(
    display_df.style.apply(alternating_rows, axis=1).format(
        {"Prevailing Price (₱)": "₱{:.2f}"}
    ),
    column_config={
        "market_name": "Market",
        "Prevailing Price (₱)": st.column_config.NumberColumn("Price", format="₱%.2f"),
        "days_ago": None,  # Hide raw
    },
    use_container_width=True,
    hide_index=True,
)

# ==========================================
# FOOTER
# ==========================================

st.caption(
    "Data Source: [Department of Agriculture - Bantay Presyo](http://www.bantaypresyo.da.gov.ph/) | © 2026 Agri-Price Intelligence Platform"
)
