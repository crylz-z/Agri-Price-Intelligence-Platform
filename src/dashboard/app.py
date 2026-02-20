import streamlit as st
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from src.core import config
from src.dashboard.utils.data_engine import DataEngine

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
# Task 1: Dynamically scan Silver directory on every reload
try:
    con = DataEngine._get_connection()
    bucket = os.getenv("S3_BUCKET_NAME")
    if bucket:
        y = datetime.today().strftime("%Y")
        m = datetime.today().strftime("%m")
        fast_silver_path = f"s3://{bucket}/silver/year={y}/month={m}/*/*.parquet"
        query = f"SELECT MAX(extract_dt) as max_date FROM read_parquet('{fast_silver_path}', union_by_name=true)"
        max_date_df = con.sql(query).df()
    else:
        max_date_df = pd.DataFrame()
    latest_date = (
        pd.to_datetime(max_date_df.iloc[0]["max_date"]).date()
        if not max_date_df.empty and pd.notnull(max_date_df.iloc[0]["max_date"])
        else datetime.today().date()
    )
    con.close()
except Exception as e:
    print(f"Max date calculation failed: {e}")
    latest_date = datetime.today().date()

# Initialize global date state silently
if "global_date" not in st.session_state:
    st.session_state["global_date"] = latest_date.strftime("%Y-%m-%d")

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
