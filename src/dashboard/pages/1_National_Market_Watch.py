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
# ROW 1: EXECUTIVE BRIEF (Commodity Level)
# ==========================================
st.markdown("---")
st.subheader(f"Executive Brief: {selected_commodity}")

# FIX: Passed commodity_df instead of category_df per user request
metrics.render_kpi_cards(commodity_df)

# Sparkline (Trend)
# Calculate trend for specific commodity
trend_df = region_df[region_df['commodity'] == selected_commodity].groupby('extract_dt')['Prevailing Price (₱)'].mean().reset_index()
metrics.render_sparklines(trend_df, selected_commodity)

# ==========================================
# ROW 1.5: REGIONAL CONTEXT (New Feature)
# ==========================================
st.markdown("---")
st.subheader(f"Regional Price Comparison: {selected_commodity}")

col_bar, col_top5 = st.columns([2, 1])

with col_bar:
    # Calculate Average Price per Region for this Commodity (Snapshot)
    # We need to load raw data for ALL regions for this date first.
    # Currently `raw_df` acts as our snapshot.
    # Filter raw_df for the selected commodity across ALL regions
    cross_region_df = raw_df[raw_df['commodity'] == selected_commodity].copy()
    
    if not cross_region_df.empty:
        reg_stats = cross_region_df.groupby('region_name')['Prevailing Price (₱)'].mean().reset_index()
        reg_stats = reg_stats.sort_values('Prevailing Price (₱)', ascending=False)
        
        # Highlight current region
        reg_stats['color'] = reg_stats['region_name'].apply(lambda x: '#ff4b4b' if x == selected_region else '#e0e0e0')
        
        chart_reg = alt.Chart(reg_stats).mark_bar().encode(
            x=alt.X('Prevailing Price (₱):Q', title='Avg Price (₱)'),
            y=alt.Y('region_name:N', sort='-x', title=None),
            color=alt.Color('color:N', scale=None),
            tooltip=['region_name', 'Prevailing Price (₱)']
        ).properties(height=300)
        st.altair_chart(chart_reg, use_container_width=True)
    else:
        st.info("No cross-regional data available.")

with col_top5:
    st.markdown("**Top 5 Most Expensive Markets**")
    if not cross_region_df.empty:
        top5 = cross_region_df.nlargest(5, 'Prevailing Price (₱)')[['region_name', 'market_name', 'Prevailing Price (₱)']]
        st.dataframe(
            top5,
            column_config={
                'region_name': 'Region',
                'market_name': 'Market',
                'Prevailing Price (₱)': st.column_config.NumberColumn("Price", format="₱%.2f")
            },
            hide_index=True,
            use_container_width=True
        )


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
