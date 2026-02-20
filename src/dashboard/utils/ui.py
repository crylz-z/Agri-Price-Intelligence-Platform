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
