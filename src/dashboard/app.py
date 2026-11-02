"""PSA monthly retail food prices.

uv run python -m streamlit run src/dashboard/app.py
"""

import streamlit as st

from src.dashboard.views import compare_page, trend_page

st.set_page_config(page_title="APIP: PH retail food prices", layout="wide")
st.navigation(
    [
        st.Page(trend_page, title="Price trend", url_path="trend", default=True),
        st.Page(compare_page, title="Compare areas", url_path="compare"),
    ]
).run()
