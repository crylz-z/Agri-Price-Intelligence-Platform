# Philippine Agri-Price Intelligence Platform (APIP) 🌾

> **"A Time Machine for Food Prices"**
> An automated data pipeline that captures, validates, and archives daily agricultural price data from the Department of Agriculture, enabling real-time inflation monitoring and arbitrage detection.

![Python](https://img.shields.io/badge/Python-3.9-blue) ![Architecture](https://img.shields.io/badge/Architecture-Matrix_Strategy-purple) ![Data](https://img.shields.io/badge/Data-Parquet-orange)

## 🚀 The Problem
The government price monitoring website is ephemeral. Data is updated daily, and historical data is deleted. This creates "Information Asymmetry" where market variances (e.g., ₱50 Corn vs ₱80 Corn) are hidden from consumers and businesses.

## 🛠️ The Solution: "The Robot"
We built a robust extraction engine that uses a **Matrix Strategy** to capture granular data across 17 Regions and 10 Commodity Categories.

### Core Architecture
1.  **Extract (The Matrix)**: Iterates through every Region-Category pair to force the API to yield data.
2.  **Route (Content-Based)**: Inspects the *actual date* inside the data payload to handle the "Midnight Bug" (where API returns yesterday's data during transition).
3.  **Transform (Silver Layer)**: Standardizes data and saves it as optimized **Parquet** files (Snappy compression).
4.  **Audit (The Bouncer)**: Automatically checks volume (>500 rows) and reach (>10 regions) before signing off.

## 📂 Project Structure
```bash
├── config/             # Configuration maps
├── data/               # The "Pantry"
│   ├── raw/            # Daily CSV snapshots (Bronze)
│   ├── clean/          # Optimized Parquet files (Silver)
│   └── reference/      # GeoJSON and SRP data
├── src/                # Source Code
│   ├── etl/            # Extraction & Transformation
│   │   ├── extract/    # extract_data.py (The Engine)
│   │   └── transform/  # clean_data.py (The Cleaner)
│   ├── dashboard/      # Streamlit App
│   │   └── app.py      # The "Bulletin Board"
│   └── validation/     # Quality Control
│       └── simple_audit.py # "The Bouncer"
└── audit_log.txt       # Daily Pass/Fail records
```

## 💻 Tech Stack
*   **Ingestion**: Python (`requests`, `BeautifulSoup`)
*   **Storage**: Parquet (PyArrow)
*   **Visualization**: Streamlit, Plotly, Folium
*   **Automation**: GitHub Actions (Planned)

## 🏃 How to Run
1.  **Run the Pipeline** (Extract -> Transform -> Audit):
    ```bash
    python src/etl/extract/extract_data.py
    ```
2.  **Launch Dashboard**:
    ```bash
    streamlit run src/dashboard/app.py
    ```
