import streamlit as st
import sys
import os
import altair as alt
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
            National Market Watch
        </h1>
        <p style="color:#6B7280; font-size:0.9rem; margin-top:0;">Real-Time Price Monitoring &amp; Intelligence</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.markdown("### Configuration")

default_date_str = st.session_state.get("global_date")
from datetime import datetime

default_date = (
    datetime.strptime(default_date_str, "%Y-%m-%d").date()
    if default_date_str
    else datetime.today().date()
)

picked_date = st.sidebar.date_input(
    "Date", value=default_date, max_value=datetime.today()
)
selected_date = picked_date.strftime("%Y-%m-%d")
st.session_state["global_date"] = selected_date

# LOAD DATA (LKGV)
raw_df = DataEngine.get_market_snapshot(selected_date)
if raw_df is None or raw_df.empty:
    st.warning(f"No data available for {selected_date}.")
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
default_cat_ix = 0
for i, cat in enumerate(valid_categories):
    if "FISH" in cat.upper():
        default_cat_ix = i
        break
selected_category = st.sidebar.selectbox(
    "Category", valid_categories, index=default_cat_ix
)
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
    selected_commodity, selected_region, days_back=30
)

# FIX: Passed commodity_df instead of category_df per user request
# NEW: Pass trend_df to enable Delta calculation
metrics.render_kpi_cards(commodity_df, trend_df)

with st.container(border=True):
    metrics.render_sparklines(trend_df, selected_commodity)

# National insight: today's price vs 30-day average + best deal market.
metrics.render_national_insight(trend_df, selected_commodity)

# ==========================================
# EXECUTIVE SUMMARY
# ==========================================

# Compute summary statistics from the current snapshot.
_national_df = raw_df[raw_df["commodity"] == selected_commodity].copy()
_national_avg = (
    _national_df["Prevailing Price (₱)"].mean() if not _national_df.empty else None
)
_market_count = commodity_df["market_name"].nunique()

# Best deal: cheapest market in the current region for the selected commodity.
_best_row = (
    commodity_df.loc[commodity_df["Prevailing Price (₱)"].idxmin()]
    if not commodity_df.empty
    else None
)
_best_market = _best_row["market_name"] if _best_row is not None else "N/A"
_best_price = _best_row["Prevailing Price (₱)"] if _best_row is not None else None

with st.expander("Executive Summary", expanded=True):
    if _national_avg is not None and _best_price is not None:
        st.markdown(
            f"""
            As of **{selected_date}**, the national average price for **{selected_commodity}** \
stands at **₱{_national_avg:,.2f}** across all reporting regions. \
In **{selected_region}**, **{_market_count}** market(s) are currently reporting prices. \
The best deal available is at **{_best_market}**, with a prevailing price of **₱{_best_price:,.2f}**.
            """
        )
    else:
        st.info("Insufficient data to generate an executive summary.")

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

        if (
            not cross_region_df.empty
            and "Prevailing Price (₱)" in cross_region_df.columns
        ):
            # 2. IQR Filter (Statistical Outlier Removal)
            if not cross_region_df.empty:
                Q1 = cross_region_df["Prevailing Price (₱)"].quantile(0.25)
                Q3 = cross_region_df["Prevailing Price (₱)"].quantile(0.75)
                IQR = Q3 - Q1
                if IQR > 0:
                    upper_bound = Q3 + 3 * IQR
                    cross_region_df = cross_region_df[
                        cross_region_df["Prevailing Price (₱)"] <= upper_bound
                    ]

        if not cross_region_df.empty:
            reg_stats = (
                cross_region_df.groupby("region_name")["Prevailing Price (₱)"]
                .mean()
                .reset_index()
            )
            reg_stats = reg_stats.sort_values("Prevailing Price (₱)", ascending=False)

            # Identify the region with the absolute lowest average price.
            min_price_region = reg_stats.loc[
                reg_stats["Prevailing Price (₱)"].idxmin(), "region_name"
            ]

            chart_reg = (
                alt.Chart(reg_stats)
                .mark_bar()
                .encode(
                    x=alt.X("Prevailing Price (₱):Q", title="Avg Price (₱)"),
                    y=alt.Y("region_name:N", sort="-x", title=None),
                    # Green for the cheapest region; neutral blue for all others.
                    color=alt.condition(
                        alt.datum.region_name == min_price_region,
                        alt.value("#2ca02c"),  # Best deal: green
                        alt.value("#1f77b4"),  # All others: neutral blue
                    ),
                    tooltip=[
                        alt.Tooltip("region_name:N", title="Region"),
                        alt.Tooltip(
                            "Prevailing Price (₱):Q",
                            title="Avg Price (₱)",
                            format=",.2f",
                        ),
                    ],
                )
                .properties(height=350)
                .configure_axis(grid=False)
            )
            st.altair_chart(chart_reg, use_container_width=True)
        else:
            st.info("No cross-regional data available.")

with col_top5:
    with st.container(border=True):
        # Use Tabs for cleaner UI
        tab_high, tab_low = st.tabs(["Most Expensive", "Best Deals"])

        # Define shared formatting function (nested to keep scope context or move out)
        def alternating_rows(row):
            color = "#F0F2F6" if row.name % 2 != 0 else "#FAFAFA"
            return ["background-color: {}".format(color) for _ in row]

        with tab_high:
            st.markdown("#### Top 5 Most Expensive")
            if not cross_region_df.empty:
                top5_high = cross_region_df.nlargest(5, "Prevailing Price (₱)")[
                    ["region_name", "market_name", "Prevailing Price (₱)"]
                ].reset_index(drop=True)

                # Rename columns for display and render as a static HTML table
                # (no horizontal scrollbar, 100% container width).
                top5_high = top5_high.rename(
                    columns={
                        "region_name": "Region",
                        "market_name": "Market",
                        "Prevailing Price (₱)": "Price (₱)",
                    }
                )
                top5_high["Price (₱)"] = top5_high["Price (₱)"].map("₱{:,.2f}".format)
                st.table(top5_high)
            else:
                st.info("No data available.")

        with tab_low:
            st.markdown("#### Top 5 Best Deals")
            if not cross_region_df.empty:
                # Smallest prices (Cheapest)
                top5_low = cross_region_df.nsmallest(5, "Prevailing Price (₱)")[
                    ["region_name", "market_name", "Prevailing Price (₱)"]
                ].reset_index(drop=True)

                # Rename columns for display and render as a static HTML table
                # (no horizontal scrollbar, 100% container width).
                top5_low = top5_low.rename(
                    columns={
                        "region_name": "Region",
                        "market_name": "Market",
                        "Prevailing Price (₱)": "Price (₱)",
                    }
                )
                top5_low["Price (₱)"] = top5_low["Price (₱)"].map("₱{:,.2f}".format)
                st.table(top5_low)
            else:
                st.info("No data available.")

# ==========================================
# ROW 2: VISUAL INTELLIGENCE
# ==========================================

# 50/50 Split per request
col_map, col_alert = st.columns(2)

with col_map:
    with st.container(border=True):
        st.markdown("#### Market Locations")
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


st.caption(
    "Data Source: [Department of Agriculture - Bantay Presyo](http://www.bantaypresyo.da.gov.ph/) | © 2026 Agri-Price Intelligence Platform"
)
