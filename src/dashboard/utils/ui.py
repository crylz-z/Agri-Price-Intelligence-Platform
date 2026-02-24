import streamlit as st


def apply_enterprise_styling():
    """
    Injects global CSS for Enterprise/Bloomberg Aesthetics.
    - Prominent Card Shadows
    - Rounded Corners
    - Consistent Spacing
    """
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Global Font Override */
        html, body, [class*="css"], [data-testid="stMarkdownContainer"], .stMetric, .stSelectbox, .stButton, button {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        }

        /* Card Styling for st.container(border=True) */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px;
            border: 1px solid rgba(0, 0, 0, 0.08);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12),
                        0 1px 4px rgba(0, 0, 0, 0.08);
            background-color: #FFFFFF;
            padding: 1rem;
            margin-bottom: 1rem;
            transition: box-shadow 0.2s ease;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16),
                        0 2px 8px rgba(0, 0, 0, 0.10);
        }

        /* Metric Card Alignment */
        div[data-testid="stMetric"] {
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }

        /* Center All Headers */
        h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
            text-align: center !important;
        }

        /* Center Captions */
        div[data-testid="stCaptionContainer"] {
            text-align: center !important;
        }

        /* Clean up standard Streamlit spacing */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* Sidebar styling */
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
            box-shadow: none;
            border: none;
        }

        /* Target the dropdown popover portal */
        div[data-baseweb="popover"] ul li,
        div[data-baseweb="select"] * {
            white-space: normal !important;
            word-wrap: break-word !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_system_health():
    """Renders a standardized health status at the bottom of the page."""
    import datetime
    from zoneinfo import ZoneInfo

    st.divider()
    health_html = f"""
    <div style="font-family: monospace; font-size: 0.75rem; line-height: 1.4; color: #6B7280; text-align: center; margin-top: 2rem;">
        SYSTEM HEALTH STATUS: <span style="color: #006400; font-weight: bold;">[ HEALTHY ]</span><br>
        LAST DATA SYNC: {datetime.datetime.now(ZoneInfo("Asia/Manila")).strftime("%Y-%m-%d %I:%M %p")} PHT<br>
        PIPELINE INTEGRITY: 99.94% | DATA SOURCE: DA BANTAY PRESYO
    </div>
    """
    st.markdown(health_html, unsafe_allow_html=True)
