# Philippine Agri-Price Intelligence Platform (APIP)

## System Overview
The Agri-Price Intelligence Platform (APIP) is an automated data pipeline and decision support system designed to capture, validate, and visualize daily agricultural price data from the Department of Agriculture. It serves as a centralized repository for market intelligence, enabling inflation monitoring, price anomaly detection, and regional arbitrage analysis.

## System Architecture

### 1. Ingestion Layer (The Matrix)
*   **Strategy**: Matrix Extraction (Region x Category Iteration).
*   **Mechanism**: The `src/etl/extract/extract_data.py` script orchestrates a concurrent scraping operation, targeting 17 regions and 10 commodity groups.
*   **Resilience**: Implements content-based routing to handle API inconsistencies and the "Midnight Bug" (data date mismatches).

### 2. Transformation Layer (Silver)
*   **Process**: Raw CSV data is ingested, cleaned, and standardized.
*   **Storage**: Data is saved as persistent Parquet files with Snappy compression to ensure high-performance I/O and reduced storage footprint.
*   **Logic**: `src/etl/transform/clean_data.py` enforces schema validation and data type casting.

### 3. Application Layer (Dashboard)
*   **Framework**: Streamlit.
*   **Modules**:
    *   **National Market Watch**: Real-time operational dashboard for daily price monitoring and gouging alerts.
    *   **Historical Trends**: Strategic view for analyzing long-term price trajectories and market volatility.

## Repository Structure

```
├── config/             # System configuration and mapping constants
├── data/               # Data storage
│   ├── raw/            # Transient raw CSV extraction snapshots
│   ├── clean/          # Production-grade Parquet files
│   └── reference/      # GeoJSON and SRP reference data
├── docs/               # Project documentation and requirements
├── src/                # Project source code
│   ├── etl/            # Extract-Transform-Load pipelines
│   │   ├── extract/    # Ingestion logic
│   │   └── transform/  # Cleaning and standardization logic
│   ├── dashboard/      # User interface and visualization components
│   └── validation/     # Data integrity and audit scripts
└── requirements.txt    # Production dependencies
```

## Setup and Execution

### Prerequisites
*   Python 3.9+
*   Recommended: Virtual Environment

### Installation
```bash
# Install dependencies using uv
uv pip install -r requirements.txt
```

### Pipeline Execution
To execute the full data pipeline (Extract -> Transform -> Audit):
```bash
python src/etl/extract/extract_data.py
```

### Dashboard Launch
To start the web application:
```bash
uv run streamlit run src/dashboard/app.py
```

## Data Dictionary
*   **region_name**: Administrative region (e.g., NCR, Region III).
*   **market_name**: Specific market location.
*   **commodity**: Full commodity name (including specifications).
*   **price**: Prevailing market price (PHP).
*   **extract_dt**: Date of data extraction (YYYY-MM-DD).
*   **uuid**: Unique record identifier.

## License
MIT
