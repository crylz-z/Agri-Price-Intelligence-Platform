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
        # Always return today's date per user preference for the calendar default
        return pht_now.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Date calculation failed: {e}")
        return datetime.now().strftime("%Y-%m-%d")


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
