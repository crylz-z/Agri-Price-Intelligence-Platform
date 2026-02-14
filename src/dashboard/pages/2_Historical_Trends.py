import streamlit as st
import sys
import os
import altair as alt
from datetime import datetime

# Ensure root is in path
if os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')) not in sys.path:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.dashboard.utils.data_engine import DataEngine

st.set_page_config(layout="wide", page_title="Historical Trends", page_icon=None)

# ==========================================
# HEADER
# ==========================================
st.title("Strategic Analysis: Historical Trends")
st.markdown("### Long-Term Price Trajectory & Volatility")

# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.header("Configuration")

# 1. Date Range
range_options = {
    "Last 7 Days": 7,
    "Last 30 Days": 30,
    "Last 90 Days": 90,
    "Year to Date": 365
}
selected_range_label = st.sidebar.selectbox("Time Horizon", list(range_options.keys()), index=1)
days_back = range_options[selected_range_label]

# 2. Region & Commodity (We need a reference to populate these, load latest available)
# We can use the DataEngine to get the latest date to bootstrap the lists
available_dates = DataEngine.get_available_dates()
if not available_dates:
    st.error("System Offline: No data available.")
    st.stop()

latest_date = available_dates[0]
reference_df = DataEngine.load_market_data(latest_date)

if reference_df is None or reference_df.empty:
    st.error("Unable to load reference metadata.")
    st.stop()

# Region
valid_regions = sorted(reference_df['region_name'].dropna().unique())
default_ix = 0
if "NCR (NATIONAL CAPITAL REGION)" in valid_regions:
    default_ix = valid_regions.index("NCR (NATIONAL CAPITAL REGION)")
selected_region = st.sidebar.selectbox("Region", valid_regions, index=default_ix)

# Commodity (Filter by Region first to be helpful)
region_ref_df = reference_df[reference_df['region_name'] == selected_region]
valid_commodities = sorted(region_ref_df['commodity'].dropna().unique())
selected_commodity = st.sidebar.selectbox("Commodity", valid_commodities)


# ==========================================
# LOAD HISTORICAL DATA
# ==========================================
with st.spinner(f"Loading {days_back} days of history for {selected_commodity}..."):
    hist_df = DataEngine.load_historical_data(selected_commodity, selected_region, days_back=days_back)

if hist_df.empty:
    st.warning(f"No historical data found for {selected_commodity} in {selected_region} over the last {days_back} days.")
    st.stop()

# ==========================================
# VISUALIZATION
# ==========================================

# METRICS SUMMARY
avg_price_period = hist_df['Prevailing Price (₱)'].mean()
min_price_period = hist_df['Prevailing Price (₱)'].min()
max_price_period = hist_df['Prevailing Price (₱)'].max()

m1, m2, m3 = st.columns(3)
m1.metric("Period Average", f"₱{avg_price_period:,.2f}")
m2.metric("Period Low", f"₱{min_price_period:,.2f}")
m3.metric("Period High", f"₱{max_price_period:,.2f}")

st.markdown("---")

# CHART 1: PRICE TRAJECTORY (Multi-Line)
st.subheader("Price Trajectory by Market")
st.caption("Tracking daily price movements across different markets in the region.")

with st.expander("How to Read This Chart", expanded=False):
    st.markdown("""
    *   **Trend Identification**: Upward sloping lines indicate inflationary pressure; downward slopes suggest supply stabilization.
    *   **Market Outliers**: Lines that deviate significantly above the group may indicate localized supply constraints or potential price gouging.
    *   **Convergence**: When lines cluster tightly together, it indicates a competitive and stable market environment.
    *   **Gaps**: Broken lines indicate days where a specific market did not report data.
    """)

# Line Chart: X=Date, Y=Price, Color=Market
line_chart = alt.Chart(hist_df).mark_line(point=True).encode(
    x=alt.X('extract_dt:T', title='Date', axis=alt.Axis(format='%b %d')),
    y=alt.Y('Prevailing Price (₱):Q', title='Price (₱)', scale=alt.Scale(zero=False)),
    color=alt.Color('market_name:N', title='Market'),
    tooltip=['extract_dt', 'market_name', 'Prevailing Price (₱)']
).properties(
    height=400
).interactive()

st.altair_chart(line_chart, use_container_width=True)

# CHART 2: VOLATILITY / SPREAD
st.markdown("---")
st.subheader("Daily Price Spread (Volatility)")
st.caption("The gap between the cheapest and most expensive market each day.")

# Calculate Daily Min/Max/Avg
daily_stats = hist_df.groupby('extract_dt')['Prevailing Price (₱)'].agg(['min', 'max', 'mean']).reset_index()
daily_stats['spread'] = daily_stats['max'] - daily_stats['min']

# Area Chart for Range
base = alt.Chart(daily_stats).encode(x=alt.X('extract_dt:T', title='Date'))

area = base.mark_area(opacity=0.3, color='gray').encode(
    y=alt.Y('min:Q', title='Price Range (₱)', scale=alt.Scale(zero=False)),
    y2='max:Q'
)

line_avg = base.mark_line(color='red').encode(
    y='mean:Q'
)

combined = (area + line_avg).properties(height=300).interactive()

st.altair_chart(combined, use_container_width=True)
st.caption("Gray Area = Price Range (Low to High). Red Line = Market Average.") 

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.caption("Data Source: [Department of Agriculture - Bantay Presyo](http://www.bantaypresyo.da.gov.ph/) | © 2026 Agri-Price Intelligence Platform") 
