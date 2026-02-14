# Dashboard Architecture & Design Audit

## 1. System Architecture
The current application leverages a **Monolithic Script-Based Architecture** powered by Streamlit.

*   **Runtime Model**: Synchronous, single-threaded execution loop. Every user interaction (filter change) triggers a full re-execution of the `main()` function from top to bottom.
*   **State Management**: Implicit Session State. The application relies on Streamlit's widget registry for state persistence (e.g., selected region) rather than a centralized store (Redux/Flux pattern).
*   **Data Access Layer**: Direct File System (DFS) Access. The application bypasses any API layer, reading Parquet files directly from disk (`data/clean/*.parquet`) using Pandas.
*   **Performance Strategy**:
    *   **Memoization**: Utilizes `@st.cache_data(ttl=600)` to store the heavy "Data Window" in RAM, preventing disk I/O on every interaction.
    *   **Lazy Loading**: Components like the Map and Deep Dive charts are computed only after the "Global Filters" are applied, reducing initial render cost.

## 2. Data Pipeline Integration (LKGV Strategy)
The dashboard implements a **Last Known Good Value (LKGV) Coalescence Logic** at the presentation layer:

1.  **Windowing**: It loads a 3-day rolling window of data (Target Date + 2 previous days).
2.  **Squashing**: It applies a `drop_duplicates` operation keyed on `(Region, Market, Commodity)`, keeping the `first` (newest) record.
3.  **Freshness Calculation**: A derived dimension `days_ago` is computed dynamically to flag stale data at the cell level.

## 3. UI/UX & Visual Design Audit

### A. Layout System
*   **Grid System**: A "Wide Pattern" layout (`layout="wide"`) utilizing a **Sidebar-Primary** split.
*   **Container Logic**: 
    *   **Zone A (KPIs)**: Uses `st.columns(3)` for a horizontal metrics spread.
    *   **Zone B (Table)**: Full-width container usage.
    *   **Zone C/D (Deep Dive)**: 50/50 Split (`st.columns([1,1])`) for Map vs. Fairness Chart.

### B. Color System (Computed)
The design currently mixes **Streamlit Default Tokens** with **Hardcoded Signal Colors**:

*   **Primary Background**: `#FFFFFF` (White) - *Implicit*.
*   **Sidebar Surface**: `rgb(240, 242, 246)` (Light Slate).
*   **Typography**: `'Source Sans Pro', sans-serif` (Computed Default).
*   **Signal Palette** (Hardcoded in Python):
    *   **Danger / High Volatility**: `#e74c3c` (Flat Red) - Used in Charts.
    *   **Safe / Stable**: `#2ecc71` (Emerald Green) - Used in Charts.
    *   **Stale Data**: `#e67e22` (Carrot Orange) - Used in Table text.
    *   **Alert Backgrounds**: `#ffe6e6` (Pale Red) - Used for Table Row Highlighting.

### C. Component Analysis (The "Broken" Card System)
*   **Intended Design**: The code defines a CSS class `.metric-card` meant to provide a "Card UI" (Border, Shadow, Padding/15px).
*   **Actual Rendering**: This CSS is **Orphaned**. The metrics are rendered using native `st.metric` calls (`<div data-testid="stMetric">`), which do *not* inherit the custom `.metric-card` class.
*   **Result**: Metrics appear floating in white space without containment, breaking the intended visual hierarchy.

## 4. Visualizations
*   **Geospatial**: `folium` (Leaflet wrapper). Uses simple CircleMarkers with binary color logic (Red/Green) based on regional average comparison.
*   **Statistical**: `plotly.express` (D3.js wrapper).
    *   **Fairness Meter**: Horizontal Bar Chart (`px.bar`) representing Z-Score deviation.
    *   **Distribution**: Box Plot (`px.box`) showing quartile distribution and outliers.

## 5. Critical Refactor Vectors
1.  **Decouple CSS**: Move styling from inline string injection to a dedicated `style.css` loaded via `st.markdown`.
2.  **Component Wrapping**: Implement a custom container function (e.g., `ui_card(content)`) to correctly apply the `.metric-card` styles that are currently ignored.
3.  **Theme Unification**: Replace hardcoded hex codes (e.g., `#e74c3c`) with Streamlit Theme config variables to support Dark Mode natively.
