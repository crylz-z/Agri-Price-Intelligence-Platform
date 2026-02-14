import streamlit as st

st.set_page_config(
    page_title="Agri-Price Intelligence",
    page_icon=None,
)

st.write("# Welcome to Agri-Price Intelligence!")

st.markdown(
    """
    This platform provides real-time monitoring of agricultural commodity prices across the Philippines.
    
    ### Select a Module from the sidebar to begin.
    
    **Available Modules:**
    - **National Market Watch**: Comprehensive dashboard for price monitoring, anomaly detection, and market analysis.
    
    ### System Status
    - **Data Pipeline**: Active (Daily Updates)
    - **Coverage**: 17 Regions
    - **Commodities**: Rice, Corn, Meat, Fish, Vegetables, Fruits
    """
)
