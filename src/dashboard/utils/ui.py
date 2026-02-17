import streamlit as st


def apply_enterprise_styling():
    """
    Injects global CSS for Enterprise/Bloomberg Aesthetics.
    - Card Shadows
    - Rounded Corners
    - Consistent Spacing
    """
    st.markdown(
        """
        <style>
        /* Card Styling for st.container(border=True) */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
                        0 2px 4px -1px rgba(0, 0, 0, 0.06);
            background-color: #FFFFFF;
            padding: 1rem;
            margin-bottom: 1rem;
            height: 100%; /* Try to fill parent */
        }

        /* Metric Card Alignment */
        div[data-testid="stMetric"] {
            min-height: 120px; /* Force taller fixed height to match multi-line text */
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center; /* Center metric content too */
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
        </style>
    """,
        unsafe_allow_html=True,
    )
