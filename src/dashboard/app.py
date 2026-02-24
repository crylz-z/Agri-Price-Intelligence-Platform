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
    page_title="Agri-Price Intelligence",
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
# Task: Cache the latest date calculation to optimize page navigation
@st.cache_data(ttl=600)
def get_latest_data_date():
    try:
        pht_tz = ZoneInfo("Asia/Manila")
        pht_now = datetime.now(pht_tz)

        con = DataEngine._get_connection()
        bucket = os.getenv("S3_BUCKET_NAME")
        if bucket:
            resilient_path = f"s3://{bucket}/silver/year=*/month=*/day=*/*.parquet"
            query = f"""
                SELECT MAX(extract_dt) as max_date
                FROM read_parquet('{resilient_path}', union_by_name=true, hive_partitioning=1)
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
        return latest_date.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Max date calculation failed: {e}")
        return datetime.now(ZoneInfo("Asia/Manila")).strftime("%Y-%m-%d")


selected_date_str = get_latest_data_date()

# Initialize global date state
if "global_date" not in st.session_state:
    st.session_state["global_date"] = selected_date_str

# --- Multipage Navigation (st.Page API) ---
home = st.Page("pages/0_Home.py", title="Home", icon=":material/home:", default=True)
regional = st.Page(
    "pages/1_Regional_Deep_Dive.py",
    title="Regional Deep Dive",
    icon=":material/zoom_in:",
)
national = st.Page(
    "pages/2_National_Macro_Watch.py",
    title="National Macro Watch",
    icon=":material/public:",
)
trends = st.Page(
    "pages/3_Historical_Trends.py",
    title="Historical Trends",
    icon=":material/timeline:",
)

pg = st.navigation([home, regional, national, trends])
pg.run()
