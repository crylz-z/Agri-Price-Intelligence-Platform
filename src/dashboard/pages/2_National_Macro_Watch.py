import streamlit as st
import sys
import os
import altair as alt
import pandas as pd
from dotenv import load_dotenv

# Load environment variables for S3 access
load_dotenv()

# Ensure root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.dashboard.utils.data_engine import DataEngine  # noqa: E402
from src.dashboard.utils import ui  # noqa: E402
from src.dashboard.components import metrics  # noqa: E402

# Apply Global Styling
ui.apply_enterprise_styling()


# ==========================================
# PAGE HEADER
# ==========================================
st.markdown(
    """
    <div style="text-align:center; margin-bottom:0.5rem;">
        <h1 style="font-size:2rem; font-weight:700; color:#1e3a5f; margin-bottom:0.1rem;">
            National Macro Watch
        </h1>
        <p style="color:#6B7280; font-size:0.9rem; margin-top:0;">17-Region Performance Comparison & National Extremes</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.markdown("### National Filters")

available_dates = DataEngine.get_available_dates()
if not available_dates:
    st.error("No data available in S3 Silver layer.")
    st.stop()

min_data_date = pd.to_datetime(available_dates[-1]).date()
max_data_date = pd.to_datetime(available_dates[0]).date()

default_date_str = st.session_state.get("global_date")
if default_date_str not in available_dates:
    default_date_str = available_dates[0]

with st.sidebar:
    selected_date = st.date_input(
        "Market Date",
        value=pd.to_datetime(default_date_str).date(),
        min_value=min_data_date,
        max_value=max_data_date,
    )
    selected_date_str = selected_date.strftime("%Y-%m-%d")

st.session_state["global_date"] = selected_date_str

# Load reference for Category/Commodity population
filter_ref_df = DataEngine.get_market_snapshot(
    selected_date_str if selected_date_str in available_dates else available_dates[0]
)

with st.sidebar:
    if filter_ref_df is not None and not filter_ref_df.empty:
        # 1. Category
        valid_categories = sorted(filter_ref_df["category"].dropna().unique().tolist())
        default_cat_ix = 0
        for i, cat in enumerate(valid_categories):
            if "RICE" in cat.upper():
                default_cat_ix = i
                break
        selected_category = st.selectbox(
            "Category", valid_categories, index=default_cat_ix
        )

        # 2. Commodity
        cat_df = filter_ref_df[filter_ref_df["category"] == selected_category]
        valid_commods = sorted(cat_df["commodity"].dropna().unique())

        default_commod_ix = 0
        if "RICE" in selected_category:
            for i, commod in enumerate(valid_commods):
                if "WELL-MILLED" in commod.upper() or "REGULAR" in commod.upper():
                    default_commod_ix = i
                    break

        selected_commodity = st.selectbox(
            "Commodity", valid_commods, index=default_commod_ix
        )
    else:
        st.info("Syncing metadata...")
        selected_category = None
        selected_commodity = None

# Soft-Fail
if selected_date_str not in available_dates:
    st.warning(f"No market data found for {selected_date_str}.")
    st.stop()

# UNIFIED SOURCE OF TRUTH (National Scope)
truth_df = DataEngine.get_truth_df(
    selected_date_str, category=selected_category, commodity=selected_commodity
)

# Load History (National Average)
trend_df = DataEngine.get_historical_trends(
    selected_commodity, None, days_back=30, end_date_str=selected_date_str
)

# ==========================================
# ROW 1: NATIONAL OVERVIEW
# ==========================================
st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, #1e3a5f 0%, #2E86AB 100%);
        color: white;
        padding: 0.75rem 1.25rem;
        border-radius: 10px;
        margin-bottom: 0.75rem;
        font-size: 1.1rem;
        font-weight: 600;
        text-align: center;
    ">
        National Snapshot: {selected_commodity}
    </div>
    """,
    unsafe_allow_html=True,
)

metrics.render_kpi_cards(truth_df, trend_df)

with st.container(border=True):
    st.markdown("#### National Price Trend (30D Avg)")
    st.caption(
        "How to read: The sparkline represents the 30-day aggregate price trajectory across all 17 regions."
    )
    metrics.render_sparklines(trend_df, selected_commodity, "PHILIPPINES (NATIONAL)")

# Insight derived from unified national data (Trend + Truth)
metrics.render_price_insight(trend_df, selected_commodity, truth_df=truth_df)

# ==========================================
# ROW 2: COMPARATIVE ANALYSIS
# ==========================================
# National Comparative Analysis: Regional Pricing Heatmap
with st.container(border=True):
    st.markdown("#### Regional Pricing Heatmap")
    st.caption(
        "How to read: 🟥 Darker Red = Higher Avg Price | 🟦 Darker Blue = Lower Avg Price. Visualizes regional variance at a glance."
    )
    if not truth_df.empty:
        reg_stats = (
            truth_df.groupby("region_name")["Prevailing Price (₱)"].mean().reset_index()
        )
        reg_stats = reg_stats.sort_values("Prevailing Price (₱)", ascending=False)

        heatmap = (
            alt.Chart(reg_stats)
            .mark_rect()
            .encode(
                x=alt.X(
                    "region_name:N",
                    sort="-y",
                    title=None,
                    axis=alt.Axis(labelAngle=-45),
                ),
                color=alt.Color(
                    "Prevailing Price (₱):Q",
                    scale=alt.Scale(scheme="redblue", reverse=True),
                    title="Avg Price (₱)",
                ),
                tooltip=["region_name", "Prevailing Price (₱)"],
            )
            .properties(height=100)
        )

        st.altair_chart(heatmap, use_container_width=True)
    else:
        st.info("No regional comparisons available.")

# ==========================================
# ROW 3: PRICE ANOMALIES (NATIONAL)
# ==========================================
with st.container(border=True):
    st.markdown("#### Dynamic Price Anomalies (National Cluster)")
    st.caption(
        "How to read: Identifies markets nationwide that significantly deviate from the global commodity median."
    )
    metrics.render_gouging_alert(truth_df)

st.caption("© 2026 Agri-Price Intelligence Platform | National Data Feed")
