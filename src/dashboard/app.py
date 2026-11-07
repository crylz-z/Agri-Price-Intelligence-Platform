"""PSA monthly retail food prices.

uv run python -m streamlit run src/dashboard/app.py
"""

import streamlit as st

from src.dashboard import views

st.set_page_config(
    page_title="PH food prices", page_icon=":material/storefront:", layout="wide"
)
# All custom CSS lives here (the dashboard-no-css hook keeps <style> out of
# views.py). Tabular digits line prices up. The rest styles page 2's hero, its
# "when to act" cards and their usual -> now tracks (views.move_cards). Colours
# are rgba mid-tones of DEARER/CHEAPER/MUTED, so they read on both themes; text
# inherits the theme's colour.
RED, GREEN, GREY = "217, 83, 74", "62, 158, 102", "138, 129, 120"
CSS = """
.stApp { font-variant-numeric: tabular-nums; }
.stApp h1 { font-variant-numeric: normal; }

.st-key-hero-up, .st-key-hero-down {
  padding: 1.6rem 1.6rem 0.6rem; border-radius: 1.4rem;
  border: 1px solid rgba(GREY, 0.22);
  box-shadow: 0 18px 40px -28px rgba(0, 0, 0, 0.35);
}
.st-key-hero-up { background:
  radial-gradient(120% 150% at 0% 0%, rgba(RED, 0.22), rgba(RED, 0.06) 45%, transparent 75%); }
.st-key-hero-down { background:
  radial-gradient(120% 150% at 0% 0%, rgba(GREEN, 0.22), rgba(GREEN, 0.06) 45%, transparent 75%); }
.hero-kicker { font-size: 0.78rem; font-weight: 700; letter-spacing: 0.16em;
  text-transform: uppercase; opacity: 0.75; display: flex; align-items: center; gap: 0.5rem; }
.hero-kicker::before { content: ""; width: 0.6rem; height: 0.6rem; border-radius: 0.15rem;
  transform: rotate(45deg); background: rgb(GREY); }
.st-key-hero-up .hero-kicker::before { background: rgb(RED); }
.st-key-hero-down .hero-kicker::before { background: rgb(GREEN); }
.hero-row { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.4rem 0.9rem;
  margin-top: 0.35rem; }
.hero-num { font-size: clamp(2.8rem, 8vw, 4.6rem); font-weight: 800; line-height: 1;
  letter-spacing: -0.035em; }
.hero-num.up { color: rgb(RED); }
.hero-num.down { color: rgb(GREEN); }
.hero-sub { font-size: 1.15rem; font-weight: 500; opacity: 0.8; }
.chips { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem; }
.chips span { padding: 0.32rem 0.8rem; border-radius: 999px; font-size: 0.85rem;
  font-weight: 600; background: rgba(GREY, 0.14); border: 1px solid rgba(GREY, 0.18); }

.moves { display: grid; gap: 0.7rem; }
.move { --c: GREY; padding: 0.85rem 1rem 0.75rem; border-radius: 1rem;
  border: 1px solid rgba(var(--c), 0.28); border-left: 4px solid rgb(var(--c));
  background: linear-gradient(100deg, rgba(var(--c), 0.17), rgba(var(--c), 0.03) 55%, transparent); }
.move.buy { --c: GREEN; }
.move.wait { --c: RED; }
.move-head { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }
.move-name { font-weight: 700; font-size: 1.05rem; }
.move-price { font-weight: 700; }
.move-price small { font-weight: 500; opacity: 0.6; }
.track { position: relative; height: 8px; margin: 0.85rem 0.5rem 0.6rem;
  border-radius: 999px; background: rgba(GREY, 0.16); }
.track .mid { position: absolute; left: 50%; top: -5px; bottom: -5px; width: 2px;
  margin-left: -1px; background: rgba(GREY, 0.7); border-radius: 1px; }
.track .bar { position: absolute; top: 0; bottom: 0; border-radius: 999px; }
.move.buy .bar { background: linear-gradient(270deg, rgba(var(--c), 0.12), rgba(var(--c), 0.75)); }
.move.wait .bar { background: linear-gradient(90deg, rgba(var(--c), 0.12), rgba(var(--c), 0.75)); }
.track .ring, .track .dot { position: absolute; top: 50%; border-radius: 50%;
  transform: translate(-50%, -50%); }
.track .ring { width: 14px; height: 14px; border: 2px solid rgba(GREY, 0.95); }
.track .dot { width: 16px; height: 16px; background: rgb(var(--c));
  box-shadow: 0 0 0 5px rgba(var(--c), 0.22); }
.move-foot { display: flex; justify-content: space-between; gap: 1rem; font-size: 0.82rem; }
.move-foot span { opacity: 0.7; }
.move-foot b { color: rgb(var(--c)); font-weight: 700; }
"""
st.html(
    "<style>"
    + CSS.replace("RED", RED).replace("GREEN", GREEN).replace("GREY", GREY)
    + "</style>"
)
st.navigation(
    {
        "Stories": [
            st.Page(
                views.today_page,
                title="This month",
                icon=":material/newspaper:",
                url_path="today",
                default=True,
            ),
            st.Page(
                views.places_page,
                title="Where you live",
                icon=":material/map:",
                url_path="places",
            ),
            st.Page(
                views.ulam_page,
                title="Ulam cost",
                icon=":material/restaurant:",
                url_path="ulam",
            ),
            st.Page(
                views.seasons_page,
                title="When to buy",
                icon=":material/calendar_month:",
                url_path="seasons",
            ),
        ],
        "Explore": [
            st.Page(
                views.lookup_page,
                title="Look up a price",
                icon=":material/search:",
                url_path="lookup",
            ),
        ],
    }
).run()
