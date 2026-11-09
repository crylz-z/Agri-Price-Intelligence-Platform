"""Who's eating the farmer's peso? PSA farm and store prices of everyday foods.

uv run python -m streamlit run src/dashboard/app.py
"""

import streamlit as st

from src.dashboard import views

st.set_page_config(
    page_title="Who's eating the farmer's peso?",
    page_icon=":material/agriculture:",
    layout="centered",
)
# The page's only CSS (ADR 18; the dashboard-no-css hook keeps <style> out of
# views.py):
# - tabular digits, so prices line up;
# - the size of the big numbers above each headline (`views.hero`; their
#   colour comes from the theme);
# - each story chart fades and rises in as it scrolls into view
#   (`views.reveal`), tied to the scroll itself. A browser without scroll-driven
#   animations, or a reader who asked for reduced motion, sees the chart as is.
st.html(
    """<style>
.stApp { font-variant-numeric: tabular-nums; }
.stApp h1 { font-variant-numeric: normal; }
[class*="st-key-hero_"] [data-testid="stMetricValue"] {
  font-size: 3.5rem; font-weight: 800; line-height: 1.05;
}
@keyframes reveal {
  from { opacity: 0; transform: translateY(32px); }
  to { opacity: 1; transform: none; }
}
@supports (animation-timeline: view()) {
  @media (prefers-reduced-motion: no-preference) {
    [class*="st-key-reveal_"] {
      animation: reveal linear both;
      animation-timeline: view();
      animation-range: entry 0% entry 80%;
    }
  }
}
</style>"""
)
views.case_page()
