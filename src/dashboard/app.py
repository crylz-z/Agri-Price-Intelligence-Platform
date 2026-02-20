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


# ==========================================
# MAIN APPLICATION
# ==========================================
