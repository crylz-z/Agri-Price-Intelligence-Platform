import streamlit as st
import folium
from streamlit_folium import st_folium


def render_market_map(
    geo_enriched_df, center_lat=14.5995, center_lon=120.9842, zoom=10
):
    """
    Renders an interactive map with market price pins.
    Uses Green (Cheap) vs Red (Expensive) logic relative to average.
    """

    # Auto-center logic using fit_bounds
    locations = []
    if not geo_enriched_df.empty:
        # Collect all coordinates
        locations = geo_enriched_df[["lat", "lon"]].values.tolist()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

    avg_price = geo_enriched_df["Prevailing Price (₱)"].mean()

    # Add Pins
    for _, row in geo_enriched_df.iterrows():
        price = row["Prevailing Price (₱)"]
        color = "green" if price <= avg_price else "red"
        tooltip_txt = f"{row['market_name']}: ₱{price:,.2f}"

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=tooltip_txt,
            popup=tooltip_txt,
        ).add_to(m)

    # Fit bounds if we have locations
    if locations:
        m.fit_bounds(locations)

    st_folium(m, height=400, returned_objects=[], width="stretch")
    st.caption("Green: Below Average | Red: Above Average")
