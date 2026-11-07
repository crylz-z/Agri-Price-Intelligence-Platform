"""PSA monthly retail food prices.

uv run python -m streamlit run src/dashboard/app.py
"""

import streamlit as st

from src.dashboard import views

st.set_page_config(
    page_title="PH food prices", page_icon=":material/storefront:", layout="wide"
)
# The only custom CSS (the dashboard-no-css hook keeps <style> out of views.py):
# tabular digits so prices line up.
st.html(
    "<style>.stApp { font-variant-numeric: tabular-nums; }"
    ".stApp h1 { font-variant-numeric: normal; }</style>"
)
st.navigation(
    [
        st.Page(
            views.overview_page,
            title="Overview",
            icon=":material/newspaper:",
            url_path="overview",
            default=True,
        ),
        st.Page(
            views.places_page,
            title="Compare places",
            icon=":material/map:",
            url_path="places",
        ),
        st.Page(
            views.lookup_page,
            title="Look up a food",
            icon=":material/search:",
            url_path="lookup",
        ),
    ]
).run()
