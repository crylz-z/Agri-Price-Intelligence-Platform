import streamlit as st
import pandas as pd
import altair as alt

def render_kpi_cards(category_df, selected_category):
    """
    Renders the top row of KPI cards:
    1. Avg Price (with Delta if possible)
    2. Best Deal (Cheapest Market)
    3. Markets Reporting (Count)
    """
    if category_df.empty:
        st.warning("No data available for KPI calculation.")
        return

    # metrics
    avg_price = category_df['Prevailing Price (₱)'].mean()
    market_count = category_df['market_name'].nunique()
    
    # Best Deal Logic
    cheapest_row = category_df.loc[category_df['Prevailing Price (₱)'].idxmin()]
    cheapest_market = cheapest_row['market_name']
    cheapest_price = cheapest_row['Prevailing Price (₱)']
    
    # Render
    c1, c2, c3 = st.columns(3)
    c1.metric("Category Avg Price", f"₱{avg_price:,.2f}")
    c2.metric("Best Deal", f"₱{cheapest_price:,.2f}", f"at {cheapest_market}")
    c3.metric("Markets Reporting", market_count)

def render_sparklines(trend_df, category_name):
    """
    Renders a clean sparkline chart for the 3-day trend.
    Expects trend_df to have ['extract_dt', 'Prevailing Price (₱)']
    """
    if trend_df.empty:
        return

    st.markdown(f"**3-Day Price Trend ({category_name})**")
    
    # Altair for better control than st.line_chart
    chart = alt.Chart(trend_df).mark_line(point=True).encode(
        x=alt.X('extract_dt:T', title=None, axis=alt.Axis(format='%b %d')),
        y=alt.Y('Prevailing Price (₱):Q', title=None, scale=alt.Scale(zero=False)),
        tooltip=['extract_dt', 'Prevailing Price (₱)']
    ).properties(
        height=100
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)

def render_gouging_alert(df, srp_df):
    """
    Scans for markets charging > 15% above SRP or Regional Average.
    Displays a Red Warning Box if found.
    """
    if df.empty:
        return

    # Prepare Data
    merged = df.copy()
    # If using SRP, we need to join. For simplification, let's look at relative outliers first
    # Or strict SRP check if SRP exists for commodity.
    
    # Let's perform a lightweight check against SRP if available
    alerts = []
    
    # Group by commodity to check
    for commodity in df['commodity'].unique():
        subset = df[df['commodity'] == commodity]
        srp_row = srp_df[srp_df['commodity'] == commodity]
        
        if not srp_row.empty:
            srp = srp_row.iloc[0]['srp']
            threshold = srp * 1.15 # 15% buffer
            
            # Find violators
            violators = subset[subset['Prevailing Price (₱)'] > threshold]
            for _, row in violators.iterrows():
                diff_pct = ((row['Prevailing Price (₱)'] - srp) / srp) * 100
                alerts.append(f"**{row['market_name']}**: {commodity} @ ₱{row['Prevailing Price (₱)']:.2f} (+{diff_pct:.0f}% vs SRP)")
                
    if alerts:
        with st.expander(f"PRICE GOUGING DETECTED ({len(alerts)} Markets)", expanded=True):
            st.error("The following markets are charging >15% above the Suggested Retail Price:")
            for a in alerts[:5]: # Show top 5 to avoid flooding
                st.markdown(f"- {a}")
            if len(alerts) > 5:
                st.caption(f"...and {len(alerts)-5} more.")
    else:
        st.success("No Price Gouging Detected (All markets within 15% of SRP).")

def render_zscore_chart(df):
    """
    Renders a bar chart showing the Z-Score (Price Fairness) for each market.
    Z > 0: Expensive (Red)
    Z < 0: Cheap (Green)
    """
    if df.empty:
        return

    # Calculate Z-Score
    mean = df['Prevailing Price (₱)'].mean()
    std = df['Prevailing Price (₱)'].std()
    
    if std == 0:
        return # No variation

    df = df.copy()
    df['z_score'] = (df['Prevailing Price (₱)'] - mean) / std
    df['color'] = df['z_score'].apply(lambda x: 'Expensive' if x > 0 else 'Cheap')

    st.markdown("**Price Fairness Index (Z-Score)**")
    
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('z_score:Q', title='Z-Score (Deviation from Average)'),
        y=alt.Y('market_name:N', sort='-x', title=None),
        color=alt.Color('color:N', scale=alt.Scale(domain=['Cheap', 'Expensive'], range=['green', 'red']), legend=None),
        tooltip=['market_name', 'Prevailing Price (₱)', 'z_score']
    ).properties(
        height=max(200, len(df) * 20)
    ).interactive()

    st.altair_chart(chart, use_container_width=True)
