import streamlit as st
import os
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
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

st.markdown(
    """
    <style>
    /* Force selectbox dropdown items to wrap text */
    div[data-baseweb="select"] ul li {
        white-space: normal !important;
        word-wrap: break-word !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

CLEAN_DATA_DIR = os.path.join(config.DATA_DIR, "clean")
REF_DATA_DIR = os.path.join(config.DATA_DIR, "reference")

# ==========================================
# DATA ENGINE & GLOBAL SIDEBAR
# Task 1: Dynamically scan Silver directory for latest data (PHT Aware)
try:
    pht_tz = ZoneInfo("Asia/Manila")
    pht_now = datetime.now(pht_tz)

    con = DataEngine._get_connection()
    bucket = os.getenv("S3_BUCKET_NAME")
    if bucket:
        # Scan current and previous month to handle month-start edge cases
        curr_y, curr_m = pht_now.strftime("%Y"), pht_now.strftime("%m")
        prev_month = pht_now.month - 1 or 12
        prev_year = pht_now.year if pht_now.month > 1 else pht_now.year - 1
        prev_m = f"{prev_month:02d}"

        # Construct paths for both months
        paths = [
            f"s3://{bucket}/silver/year={curr_y}/month={curr_m}/*/*.parquet",
            f"s3://{bucket}/silver/year={prev_year}/month={prev_m}/*/*.parquet",
        ]

        query = f"""
            SELECT MAX(extract_dt) as max_date
            FROM read_parquet({paths}, union_by_name=true)
            WHERE TRY_CAST(extract_dt AS DATE) <= '{pht_now.date()}'
        """
        max_date_df = con.sql(query).df()
    else:
        max_date_df = pd.DataFrame()

    latest_date = (
        pd.to_datetime(max_date_df.iloc[0]["max_date"]).date()
        if not max_date_df.empty and pd.notnull(max_date_df.iloc[0]["max_date"])
        else pht_now.date()
    )
    con.close()
except Exception as e:
    print(f"Max date calculation failed: {e}")
    latest_date = datetime.now(ZoneInfo("Asia/Manila")).date()

# Initialize global date state
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
