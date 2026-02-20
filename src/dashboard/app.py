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
    page_icon="🇵🇭",
)

CLEAN_DATA_DIR = os.path.join(config.DATA_DIR, "clean")
REF_DATA_DIR = os.path.join(config.DATA_DIR, "reference")


# ==========================================
# DATA ENGINE & GLOBAL SIDEBAR
# ==========================================
from src.dashboard.utils.data_engine import DataEngine, SILVER_LAYER_PATH
import duckdb

st.sidebar.header("Global Configuration")

# Task 1: Dynamically scan Silver directory on every reload
try:
    con = DataEngine._get_connection()
    query = f"SELECT MAX(extract_dt) as max_date FROM read_parquet('{SILVER_LAYER_PATH}', union_by_name=true)"
    max_date_df = con.sql(query).df()
    latest_date = (
        pd.to_datetime(max_date_df.iloc[0]["max_date"]).date()
        if not max_date_df.empty and pd.notnull(max_date_df.iloc[0]["max_date"])
        else datetime.today().date()
    )
    con.close()
except Exception:
    latest_date = datetime.today().date()

# explicitly apply max_value=latest_date
picked_date = st.sidebar.date_input("Date", value=latest_date, max_value=latest_date)
st.session_state["global_date"] = picked_date.strftime("%Y-%m-%d")

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


@st.cache_data(ttl=600)
def load_data_window(target_date_str, window_days=3):
    """
    LKGV Strategy: Loads a window of data (Target + Previous Days).
    Returns a combined raw DataFrame.
    """
    from src.dashboard.utils.data_engine import DataEngine, SILVER_LAYER_PATH

    if not SILVER_LAYER_PATH:
        return None

    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        start_date = target_date - timedelta(days=window_days)
        start_date_str = start_date.strftime("%Y-%m-%d")

        con = DataEngine._get_connection()
        query = f"""
        SELECT *
        FROM read_parquet('{SILVER_LAYER_PATH}', union_by_name=true, hive_partitioning=1)
        WHERE CAST(extract_dt AS DATE) BETWEEN '{start_date_str}' AND '{target_date_str}'
        """
        df = con.sql(query).df()
        con.close()

        if "extract_dt" in df.columns:
            df["extract_dt"] = pd.to_datetime(df["extract_dt"])

        return df if not df.empty else None
    except Exception as e:
        print(f"Error loading local silver dbt paths: {e}")
        return None


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
