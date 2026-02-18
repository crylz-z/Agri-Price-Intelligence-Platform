import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# --- Multipage Navigation (st.Page API) ---
home = st.Page("pages/0_Home.py", title="Home", icon=":material/home:", default=True)
market = st.Page("pages/1_National_Market_Watch.py", title="National Market Watch", icon=":material/monitoring:")
trends = st.Page("pages/2_Historical_Trends.py", title="Historical Trends", icon=":material/timeline:")

pg = st.navigation([home, market, trends])
st.set_page_config(page_title="Agri-Price Intelligence Platform", page_icon="🇵🇭", layout="wide")
pg.run()
