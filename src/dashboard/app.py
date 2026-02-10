import streamlit as st
import pandas as pd
import glob
import os
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Agri-Price Intelligence Platform",
    page_icon="🌾",
    layout="wide"
)

# --- LOADER ---
@st.cache_data
def load_data():
    # Find all CSVs in data/raw
    files = glob.glob('data/raw/*.csv')
    if not files:
        return pd.DataFrame()
    
    # Load all and concat (robustness)
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            # Ensure date column is datetime
            if 'extract_dt' not in df.columns:
                 # Fallback: extract from filename
                 date_str = os.path.basename(f).replace('ncr_prices_', '').replace('.csv', '')
                 df['extract_dt'] = date_str
            dfs.append(df)
        except Exception as e:
            st.error(f"Error loading {f}: {e}")
            
    if not dfs:
        return pd.DataFrame()
        
    final_df = pd.concat(dfs, ignore_index=True)
    final_df['extract_dt'] = pd.to_datetime(final_df['extract_dt'])
    
    # Clean Price Column (force numeric)
    final_df['price'] = pd.to_numeric(final_df['price'], errors='coerce')
    final_df = final_df.dropna(subset=['price'])
    
    return final_df

# --- MAIN APP ---
def main():
    st.title("🌾 Agri-Price Intelligence Platform")
    st.markdown("Monitor daily agricultural prices in NCR wet markets.")

    df = load_data()
    
    if df.empty:
        st.warning("No data found in `data/raw/`. Run the scraper first!")
        return

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("🔍 Filters")
    
    # Date Filter
    available_dates = df['extract_dt'].dt.date.unique()
    selected_date = st.sidebar.selectbox("Select Date", sorted(available_dates, reverse=True))
    
    # Filter by Date
    daily_df = df[df['extract_dt'].dt.date == selected_date]
    
    # Category Filter
    categories = sorted(daily_df['category'].unique())
    selected_category = st.sidebar.selectbox("Category", categories)
    
    # Commodity Filter
    cat_df = daily_df[daily_df['category'] == selected_category]
    commodities = sorted(cat_df['commodity'].unique())
    selected_commodity = st.sidebar.selectbox("Commodity", commodities)
    
    # Final Filtered Data
    item_df = cat_df[cat_df['commodity'] == selected_commodity]
    
    # --- METRICS ---
    st.markdown("### 📊 Market Snapshot")
    col1, col2, col3, col4 = st.columns(4)
    
    min_price = item_df['price'].min()
    max_price = item_df['price'].max()
    avg_price = item_df['price'].mean()
    spread = max_price - min_price
    
    col1.metric("Lowest Price", f"₱{min_price:,.2f}")
    col2.metric("Highest Price", f"₱{max_price:,.2f}")
    col3.metric("Average Price", f"₱{avg_price:,.2f}")
    col4.metric("Arbitrage Spread", f"₱{spread:,.2f}", help="Difference between highest and lowest price")
    
    st.markdown("---")
    
    # --- VISUALIZATION ---
    col_chart, col_table = st.columns([2, 1])
    
    with col_chart:
        st.subheader(f"🏷️ Price Distribution: {selected_commodity}")
        
        # Sort by price for better visualization
        sorted_df = item_df.sort_values('price')
        
        # Color logic: Green (Cheap) -> Red (Expensive)
        fig = px.bar(
            sorted_df, 
            x='price', 
            y='market_name',
            orientation='h',
            title=f"Prices by Market ({selected_commodity})",
            labels={'market_name': 'Market', 'price': 'Price (PHP)'},
            color='price',
            color_continuous_scale='RdYlGn_r', # Red-Yellow-Green (Reverse)
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col_table:
        st.subheader("📋 Raw Data")
        st.dataframe(
            item_df[['market_name', 'price']].sort_values('price'),
            hide_index=True,
            use_container_width=True
        )

if __name__ == "__main__":
    main()
