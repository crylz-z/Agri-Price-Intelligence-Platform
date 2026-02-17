import streamlit as st
import pandas as pd
import glob
import os
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables for S3 access
load_dotenv()

# Import S3-enabled Data Engine
from src.dashboard.utils.data_engine import DataEngine

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(
    layout="wide", page_title="Market Bulletin | Agri-Price Intelligence", page_icon="📋"
)
REF_DATA_DIR = "data/reference"

# PROFESSIONAL STYLE
st.markdown(
    """
<style>

    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; }
    .stDataFrame { border: 1px solid #f0f0f0; }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# DATA ENGINE
# ==========================================



@st.cache_data
def load_reference_data():
    """Loads SRP and Lat/Lon data safely."""
    return DataEngine.load_reference_data()


def get_available_dates():
    """Gets available dates from S3 Gold layer."""
    return DataEngine.get_available_dates()


# ==========================================
# MAIN APPLICATION
# ==========================================


def main():
    st.title("Official Market Bulletin")

    # ---------------------------
    # SIDEBAR: HIERARCHY
    # ---------------------------
    st.sidebar.header("Configuration")

    # LEVEL 1: DATE (Global)
    available_dates = get_available_dates()
    if not available_dates:
        st.error("System Offline: No data available.")
        return
    selected_date = st.sidebar.selectbox("Date", available_dates)

    # LOAD DATA from S3 Gold Layer (Last Known Good Value strategy)
    raw_df = DataEngine.get_market_snapshot(selected_date, window_days=3)

    if raw_df is None or raw_df.empty:
        st.error(f"System Offline: Unable to load data window for {selected_date}.")
        return

    # COALESCE (The "Squash" Operation)
    # 1. Sort by Date Descending (Newest first)
    raw_df = raw_df.sort_values("extract_dt", ascending=False)

    # RENAME COLUMN
    # Rename verbose or simple 'price' to 'Prevailing Price (₱)'
    if "price" in raw_df.columns:
        raw_df.rename(columns={"price": "Prevailing Price (₱)"}, inplace=True)
    elif "PREVAILING RETAIL PRICE PER UNIT (P/UNIT)" in raw_df.columns:
        raw_df.rename(
            columns={
                "PREVAILING RETAIL PRICE PER UNIT (P/UNIT)": "Prevailing Price (₱)"
            },
            inplace=True,
        )

    # 2. Dedup (Keep first/newest)
    # Natural Key: Region + Market + Commodity.
    # Note: 'category' is implied by commodity but good to keep if present.
    df = raw_df.drop_duplicates(
        subset=["region_name", "market_name", "commodity"], keep="first"
    ).copy()

    # 3. Calculate Freshness
    target_dt = datetime.strptime(selected_date, "%Y-%m-%d")
    df["days_ago"] = (target_dt - df["extract_dt"]).dt.days
    df["days_ago"] = df["days_ago"].fillna(0).astype(int)

    # LEVEL 2: REGION (Global)
    valid_regions = sorted(df["region_name"].dropna().unique())
    # Default to NCR if available
    default_ix = 0
    if "NCR (NATIONAL CAPITAL REGION)" in valid_regions:
        default_ix = valid_regions.index("NCR (NATIONAL CAPITAL REGION)")

    selected_region = st.sidebar.selectbox("Region", valid_regions, index=default_ix)

    # FILTER STEP 1
    region_df = df[df["region_name"] == selected_region].copy()

    # LEVEL 3: CATEGORY (Primary Filter)
    valid_categories = sorted(region_df["category"].dropna().unique())
    selected_category = st.sidebar.selectbox("Category", valid_categories)

    # FILTER STEP 2
    category_df = region_df[region_df["category"] == selected_category].copy()

    # LEVEL 4: COMMODITY (Secondary Filter for Drill-Down)
    valid_commodities = sorted(category_df["commodity"].dropna().unique())
    selected_commodity = st.sidebar.selectbox(
        "Deep Dive Commodity", valid_commodities, index=0
    )

    # FILTER STEP 3
    commodity_df = category_df[category_df["commodity"] == selected_commodity].copy()

    # LOAD REFERENCE
    geo_df, srp_df = load_reference_data()

    # ==========================================
    # ZONE A: EXECUTIVE BRIEF (Category Level)
    # ==========================================
    st.subheader(f"Executive Brief: {selected_category} in {selected_region}")

    # Category Stats
    avg_price = category_df["Prevailing Price (₱)"].mean()
    min_price = category_df["Prevailing Price (₱)"].min()
    max_price = category_df["Prevailing Price (₱)"].max()
    volatility = ((max_price - min_price) / avg_price) * 100 if avg_price > 0 else 0

    # Status Banner
    if volatility > 20:
        st.warning(
            f"High Volatility Detected: Prices in this category vary by {volatility:.0f}%. Check for outliers."
        )
    elif volatility < 10:
        st.success(
            f"Stable Market: Price variance is low ({volatility:.0f}%) across commodities."
        )
    else:
        st.info(f"Moderate Activity: Standard price fluctuations observed.")

    # KPI Cards
    k1, k2, k3 = st.columns(3)
    k1.metric("Markets Reporting", category_df["market_name"].nunique())
    k2.metric("Category Avg Price", f"₱{avg_price:,.2f}")
    k3.metric("Commodities Tracked", category_df["commodity"].nunique())

    # SPARKLINES (3-Day Trend)
    # Get trend for this category across the loaded window
    trend_df = (
        region_df[region_df["category"] == selected_category]
        .groupby("extract_dt")["Prevailing Price (₱)"]
        .mean()
        .reset_index()
    )
    if not trend_df.empty:
        st.caption("3-Day Price Trend (Category Avg)")
        st.line_chart(trend_df.set_index("extract_dt"), height=100)

    st.markdown("---")

    # ==========================================
    # ZONE B: OFFICIAL PRICE BULLETIN (The Hero)
    # ==========================================
    st.subheader("Official Price Bulletin")

    # Aggregate Live Data by Commodity
    # We aggregate Price (mean) and Days Ago (max - being conservative, showing staleness if any)
    bulletin_df = (
        category_df.groupby("commodity")
        .agg(
            {
                "Prevailing Price (₱)": "mean",
                "days_ago": "max"  # If one market is stale, we warn? Or 'min' (best case)?
                # Let's use 'max' (Worst Case) to be transparent.
            }
        )
        .reset_index()
    )

    bulletin_df.rename(columns={"Prevailing Price (₱)": "Live Avg"}, inplace=True)

    # Merge with SRP (Left Join to keep all live commodities)
    # Ensure join on commodity name
    bulletin_df = bulletin_df.merge(srp_df, on="commodity", how="left")

    # Logic
    def get_status(row):
        live = row["Live Avg"]
        srp = row["srp"]
        if pd.isna(srp):
            return "N/A"
        if live > (srp * 1.10):
            return "High"
        if live < (srp * 0.90):
            return "Low"
        return "Fair"

    bulletin_df["Status"] = bulletin_df.apply(get_status, axis=1)
    bulletin_df["Diff"] = bulletin_df["Live Avg"] - bulletin_df["srp"]

    # Formatting Helpers
    def format_currency(val):
        return f"₱{val:,.2f}" if pd.notnull(val) else "—"

    def format_diff(val):
        if pd.isna(val):
            return "—"
        return f"{val:+.2f}"

    def format_freshness(days):
        if days == 0:
            return "Today"
        if days == 1:
            return "Yesterday"
        return f"{days} Days Ago"

    bulletin_df["Data As Of"] = bulletin_df["days_ago"].apply(format_freshness)

    # Display Table
    st.dataframe(
        bulletin_df.style.apply(
            lambda x: ["background-color: #ffe6e6" if "High" in v else "" for v in x],
            subset=["Status"],
        )
        .apply(
            lambda x: [
                "color: #e67e22; font-weight: bold" if v > 0 else "color: #2ecc71"
                for v in x
            ],
            subset=["days_ago"],
        )
        .format(
            {"Live Avg": format_currency, "srp": format_currency, "Diff": format_diff}
        ),
        column_order=["commodity", "srp", "Live Avg", "Diff", "Status", "Data As Of"],
        column_config={
            "commodity": "Commodity",
            "srp": "Prevailing Price (SRP)",
            "Live Avg": "Current Avg Price",
            "Diff": "Variance",
            "Data As Of": "Freshness",
        },
        use_container_width=True,
        hide_index=True,
    )

    # ==========================================
    # DRILL DOWN SECTION
    # ==========================================
    st.markdown("---")
    st.markdown("---")
    st.header(f"Deep Dive: {selected_commodity}")

    if commodity_df.empty:
        st.warning(f"No live data for **{selected_commodity}** today.")
        return

    col_map, col_chart = st.columns([1, 1])

    # ==========================================
    # ZONE C: GEOSPATIAL MAP (Always-On)
    # ==========================================
    with col_map:
        st.subheader("Market Location")

        # Merge Geo
        map_df = commodity_df.merge(geo_df, on="market_name", how="inner")

        # Default Center (NCR)
        default_lat, default_lon = 14.5995, 120.9842
        default_zoom = 10

        if not map_df.empty:
            avg_comm_price = commodity_df["Prevailing Price (₱)"].mean()
            center_lat = map_df["lat"].mean()
            center_lon = map_df["lon"].mean()

            m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

            for _, row in map_df.iterrows():
                price = row["Prevailing Price (₱)"]
                color = "green" if price <= avg_comm_price else "red"
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=8,
                    color=color,
                    fill=True,
                    fill_color=color,
                    tooltip=f"{row['market_name']}: ₱{price:,.2f}",
                ).add_to(m)

            st_folium(m, height=400, use_container_width=True)
            st.caption("Green: Below Regional Avg | Red: Above Regional Avg")
        else:
            # Fallback Map
            m = folium.Map(location=[default_lat, default_lon], zoom_start=default_zoom)
            st_folium(m, height=400, use_container_width=True)
            st.warning("Specific market coordinates not available.")

    # ==========================================
    # ZONE D: ANALYTICS
    # ==========================================
    with col_chart:
        st.subheader("Price Fairness")

        # Z-Score
        if commodity_df["Prevailing Price (₱)"].std() > 0:
            commodity_df["z_score"] = (
                commodity_df["Prevailing Price (₱)"]
                - commodity_df["Prevailing Price (₱)"].mean()
            ) / commodity_df["Prevailing Price (₱)"].std()
            commodity_df["color"] = commodity_df["z_score"].apply(
                lambda x: "#e74c3c" if x > 0 else "#2ecc71"
            )

            fig = px.bar(
                commodity_df,
                y="market_name",
                x="z_score",
                orientation="h",
                title="Fairness Meter (Z-Score)",
                text=commodity_df["Prevailing Price (₱)"].apply(lambda x: f"₱{x:.0f}"),
            )
            fig.update_traces(marker_color=commodity_df["color"])
            fig.add_vline(x=0, line_dash="dash", line_color="black")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("How to read: Bars to the RIGHT are expensive markets.")
        else:
            st.info("Price is uniform across all markets (No Variance).")

    # REMOVED BOX PLOT ROW AS REQUESTED


if __name__ == "__main__":
    main()
