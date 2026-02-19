import streamlit as st
import os
import glob
import pandas as pd
import folium
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.core import config

load_dotenv()

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(
    layout="wide",
    page_title="Market Bulletin | Agri-Price Intelligence",
    page_icon="📋",
)

CLEAN_DATA_DIR = os.path.join(config.DATA_DIR, "clean")
REF_DATA_DIR = os.path.join(config.DATA_DIR, "reference")


# --- Multipage Navigation (st.Page API) ---
home = st.Page("pages/0_Home.py", title="Home", icon=":material/home:", default=True)
market = st.Page(
    "pages/1_National_Market_Watch.py",
    title="National Market Watch",
    icon=":material/monitoring:",
)
trends = st.Page(
    "pages/2_Historical_Trends.py",
    title="Historical Trends",
    icon=":material/timeline:",
)

pg = st.navigation([home, market, trends])
pg.run()

# ==========================================
# DATA ENGINE
# ==========================================


@st.cache_data(ttl=600)
def load_data_window(target_date_str, window_days=3):
    """
    LKGV Strategy: Loads a window of data (Target + Previous Days).
    Returns a combined raw DataFrame.
    """
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    except Exception:
        return None

    frames = []

    for i in range(window_days):
        current_date = target_date - timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        # Try finding parquet file
        filepath = os.path.join(CLEAN_DATA_DIR, f"market_prices_{date_str}.parquet")

        try:
            if os.path.exists(filepath):
                df = pd.read_parquet(filepath)
                # Ensure extract_dt is datetime
                if "extract_dt" in df.columns:
                    df["extract_dt"] = pd.to_datetime(df["extract_dt"])
                frames.append(df)
        except Exception:
            continue

    if not frames:
        return None

    return pd.concat(frames, ignore_index=True)


@st.cache_data
def load_reference_data():
    """Loads SRP and Lat/Lon data safely."""
    # 1. GEO DATA
    geo_path = os.path.join(REF_DATA_DIR, "markets_geo.csv")
    if os.path.exists(geo_path):
        geo_df = pd.read_csv(geo_path)
    else:
        geo_df = pd.DataFrame(columns=["market_name", "lat", "lon"])

    # 2. SRP DATA
    srp_path = os.path.join(REF_DATA_DIR, "official_srp.csv")
    if os.path.exists(srp_path):
        srp_df = pd.read_csv(srp_path)
        if "official_srp" in srp_df.columns:
            srp_df.rename(columns={"official_srp": "srp"}, inplace=True)
    else:
        srp_df = pd.DataFrame(columns=["commodity", "srp"])

    return geo_df, srp_df


def get_available_dates():
    """Scans for available parquet files."""
    if not os.path.exists(CLEAN_DATA_DIR):
        return []

    files = glob.glob(os.path.join(CLEAN_DATA_DIR, "market_prices_*.parquet"))
    dates = []
    for f in files:
        basename = os.path.basename(f)
        try:
            date_str = basename.replace("market_prices_", "").replace(".parquet", "")
            dates.append(date_str)
        except Exception:
            continue
    return sorted(dates, reverse=True)


# ==========================================
# MAIN APPLICATION
# ==========================================


def main():
    st.title("📋 Official Market Bulletin")

    # ---------------------------
    # SIDEBAR: HIERARCHY
    # ---------------------------
    st.sidebar.header("Configuration")

    # LEVEL 1: DATE (Global)
    available_dates = get_available_dates()
    if not available_dates:
        st.error(f"System Offline: No data available in {CLEAN_DATA_DIR}.")
        return
    selected_date = st.sidebar.selectbox("Date", available_dates)

    # LOAD DATA (LKGV)
    raw_df = load_data_window(selected_date)

    if raw_df is None or raw_df.empty:
        st.error(f"System Offline: Unable to load data window for {selected_date}.")
        return

    # COALESCE (The "Squash" Operation)
    # 1. Sort by Date Descending (Newest first)
    raw_df = raw_df.sort_values("extract_dt", ascending=False)

    # 2. Dedup (Keep first/newest)
    # Natural Key: Region + Market + Commodity.
    df = raw_df.drop_duplicates(
        subset=["region_name", "market_name", "commodity"], keep="first"
    ).copy()

    # 3. Calculate Freshness
    target_dt = datetime.strptime(selected_date, "%Y-%m-%d")
    df["days_ago"] = (target_dt - df["extract_dt"]).dt.days
    df["days_ago"] = df["days_ago"].fillna(0).astype(int)

    # LEVEL 2: REGION (Global)
    if "region_name" not in df.columns:
        st.error("Data integrity error: 'region_name' column missing.")
        return

    valid_regions = sorted(df["region_name"].dropna().unique())
    selected_region = st.sidebar.selectbox("Region", valid_regions)

    # FILTER STEP 1
    region_df = df[df["region_name"] == selected_region].copy()

    # LEVEL 3: CATEGORY (Primary Filter)
    if "category" not in region_df.columns:
        st.error("Data integrity error: 'category' column missing.")
        return

    valid_categories = sorted(region_df["category"].dropna().unique())
    selected_category = st.sidebar.selectbox("Category", valid_categories)

    # FILTER STEP 2
    category_df = region_df[region_df["category"] == selected_category].copy()

    # LEVEL 4: COMMODITY (Secondary Filter for Drill-Down)
    if "commodity" not in category_df.columns:
        st.error("Data integrity error: 'commodity' column missing.")
        return

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
    avg_price = category_df["price"].mean()
    min_price = category_df["price"].min()
    max_price = category_df["price"].max()
    volatility = ((max_price - min_price) / avg_price) * 100 if avg_price > 0 else 0

    # Status Banner
    if volatility > 20:
        st.warning(
            f"⚠️ **High Volatility Detected**: Prices in this category vary by {volatility:.0f}%. Check for outliers."
        )
    elif volatility < 10:
        st.success(
            f"✅ **Stable Market**: Price variance is low ({volatility:.0f}%) across commodities."
        )
    else:
        st.info("ℹ️ **Moderate Activity**: Standard price fluctuations observed.")

    # KPI Cards
    k1, k2, k3 = st.columns(3)
    k1.metric("Markets Reporting", category_df["market_name"].nunique())
    k2.metric("Category Avg Price", f"₱{avg_price:,.2f}")
    k3.metric("Commodities Tracked", category_df["commodity"].nunique())

    st.markdown("---")

    # ==========================================
    # ZONE B: OFFICIAL PRICE BULLETIN (The Hero)
    # ==========================================
    st.subheader("📢 Official Price Bulletin")

    # Aggregate Live Data by Commodity
    # We aggregate Price (mean) and Days Ago (max - being conservative, showing staleness if any)
    bulletin_df = (
        category_df.groupby("commodity")
        .agg(
            {
                "price": "mean",
                "days_ago": "max",  # If one market is stale, we warn? Or 'min' (best case)?
                # Let's use 'max' (Worst Case) to be transparent.
            }
        )
        .reset_index()
    )

    bulletin_df.rename(columns={"price": "Live Avg"}, inplace=True)

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
            return "High 🔺"
        if live < (srp * 0.90):
            return "Low 📉"
        return "Fair ✅"

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
    st.header(f"🔍 Deep Dive: {selected_commodity}")

    if commodity_df.empty:
        st.warning(f"No live data for **{selected_commodity}** today.")
        return

    col_map, col_chart = st.columns([1, 1])

    # ==========================================
    # ZONE C: GEOSPATIAL MAP
    # ==========================================
    with col_map:
        st.subheader("📍 Market Location")

        # Merge Geo
        map_df = commodity_df.merge(geo_df, on="market_name", how="inner")

        if not map_df.empty:
            avg_comm_price = commodity_df["price"].mean()
            center_lat = map_df["lat"].mean()
            center_lon = map_df["lon"].mean()

            m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

            for _, row in map_df.iterrows():
                price = row["price"]
                color = "green" if price <= avg_comm_price else "red"
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=8,
                    color=color,
                    fill=True,
                    fill_color=color,
                    tooltip=f"{row['market_name']}: ₱{price:,.2f}",
                ).add_to(m)

            import streamlit_folium

            streamlit_folium.st_folium(m, height=400, use_container_width=True)
            st.caption("Green: Below Regional Avg | Red: Above Regional Avg")
        else:
            st.info("Geographic data not available for these markets.")

    # ==========================================
    # ZONE D: ANALYTICS
    # ==========================================
    with col_chart:
        st.subheader("📊 Price Fairness")

        # Z-Score
        if commodity_df["price"].std() > 0:
            commodity_df["z_score"] = (
                commodity_df["price"] - commodity_df["price"].mean()
            ) / commodity_df["price"].std()
            commodity_df["color"] = commodity_df["z_score"].apply(
                lambda x: "#e74c3c" if x > 0 else "#2ecc71"
            )

            import plotly.express as px

            fig = px.bar(
                commodity_df,
                y="market_name",
                x="z_score",
                orientation="h",
                title="Fairness Meter (Z-Score)",
                text=commodity_df["price"].apply(lambda x: f"₱{x:.0f}"),
            )
            fig.update_traces(marker_color=commodity_df["color"])
            fig.add_vline(x=0, line_dash="dash", line_color="black")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("How to read: Bars to the RIGHT are expensive markets.")
        else:
            st.info("Price is uniform across all markets (No Variance).")

    # Box Plot Row
    st.subheader("📈 Price Distribution")
    import plotly.express as px

    fig_box = px.box(
        commodity_df,
        x="price",
        points="all",
        height=200,
        title=f"Price Range for {selected_commodity}",
    )
    st.plotly_chart(fig_box, use_container_width=True)
    st.caption(
        "How to read: Dots outside the box are outliers (potential price gouging)."
    )


if __name__ == "__main__":
    main()
