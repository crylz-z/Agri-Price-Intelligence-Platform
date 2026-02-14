import streamlit as st
import sys
import os

# Ensure root is in path to find components
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Add src parent dir so we can import 'src'
# The goal is for `import src` to work
# If script is in D:/.../src/dashboard/pages
# dirname = .../pages
# .. = .../dashboard
# ../.. = .../src
# ../../.. = .../ (project root)
# then from src... works
if os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')) not in sys.path:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.dashboard.utils.data_engine import DataEngine
from src.dashboard.components import metrics, spatial

st.set_page_config(layout="wide", page_title="National Market Watch", page_icon=None)

# ==========================================
# PAGE HEADER
# ==========================================
st.title("National Market Watch")
st.markdown("### Real-Time Price Monitoring & Intelligence")




# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.header("Configuration")

# 1. Date
available_dates = DataEngine.get_available_dates()
if not available_dates:
    st.error("System Offline: No data available.")
    st.stop()
    
selected_date = st.sidebar.selectbox("Date", available_dates)

# LOAD DATA (LKGV)
raw_df = DataEngine.load_market_data(selected_date)
if raw_df is None or raw_df.empty:
    st.error(f"System Offline: Unable to load data window for {selected_date}.")
    st.stop()

# 2. Region
valid_regions = sorted(raw_df['region_name'].dropna().unique())
default_ix = 0
if "NCR (NATIONAL CAPITAL REGION)" in valid_regions:
    default_ix = valid_regions.index("NCR (NATIONAL CAPITAL REGION)")
    
selected_region = st.sidebar.selectbox("Region", valid_regions, index=default_ix)
region_df = raw_df[raw_df['region_name'] == selected_region].copy()

# 3. Category
valid_categories = sorted(region_df['category'].dropna().unique())
selected_category = st.sidebar.selectbox("Category", valid_categories)
category_df = region_df[region_df['category'] == selected_category].copy()

# 4. Commodity
valid_commodities = sorted(category_df['commodity'].dropna().unique())
selected_commodity = st.sidebar.selectbox("Commodity Focus", valid_commodities)
commodity_df = category_df[category_df['commodity'] == selected_commodity].copy()

# LOAD REF
geo_df, srp_df = DataEngine.load_reference_data()


# ==========================================
# ROW 1: EXECUTIVE BRIEF (Category Level)
# ==========================================
st.markdown("---")
st.subheader(f"Executive Brief: {selected_category}")

metrics.render_kpi_cards(category_df, selected_category)

# Sparkline (Trend)
# Calculate trend for entire category
trend_df = region_df[region_df['category'] == selected_category].groupby('extract_dt')['Prevailing Price (₱)'].mean().reset_index()
metrics.render_sparklines(trend_df, selected_category)


# ==========================================
# ROW 2: VISUAL INTELLIGENCE
# ==========================================
st.markdown("---")
col_map, col_alert = st.columns([2, 1])

with col_map:
    st.subheader(f"Market Locations: {selected_commodity}")
    # Enhance specific commodity data with Geo
    # This uses the Resilient Geo-Join from Data Engine
    geo_enriched = DataEngine.enrich_with_geo(commodity_df, geo_df)
    
    # Render Map Feature
    spatial.render_market_map(geo_enriched)

with col_alert:
    st.subheader("Price Watch")
    # Check for Gouging
    metrics.render_gouging_alert(commodity_df, srp_df)

    # Z-Score Chart (Restored)
    metrics.render_zscore_chart(commodity_df)


# ==========================================
# ROW 3: THE LEDGER
# ==========================================
st.markdown("---")
st.subheader("Official Price Bulletin")

# Format for display
display_df = commodity_df[['market_name', 'commodity', 'Prevailing Price (₱)', 'days_ago']].copy()
display_df['Freshness'] = display_df['days_ago'].apply(lambda x: "Today" if x==0 else f"{x} days ago")

st.dataframe(
    display_df,
    column_config={
        'market_name': 'Market',
        'Prevailing Price (₱)': st.column_config.NumberColumn("Price", format="₱%.2f"),
        'days_ago': None # Hide raw
    },
    use_container_width=True,
    hide_index=True
)
