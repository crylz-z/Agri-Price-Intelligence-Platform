# Agri-Price Intelligence Platform

## System Architecture

The platform uses a modern **ELT (Extract, Load, Transform)** architecture orchestrated by GitHub Actions.

### Architecture Overview

1.  **Ingestion:** The **dlt (Data Load Tool)** pipeline scrapes daily price updates from the DA-AMAS website and writes raw data to the **Bronze Layer** (AWS S3) as partitioned Parquet files.
2.  **Transformation:** **dbt Core** (with DuckDB) reads Bronze data directly from S3, cleans and standardizes it into the **Silver Layer**, and aggregates business metrics into the **Gold Layer**.
3.  **Consumption:** The **Streamlit Dashboard** queries the Gold Layer Parquet files directly using DuckDB for high-performance OLAP analysis.
4.  **Orchestration:** A Python script (`run_pipeline.py`) manages the end-to-end flow, enforcing a **WAP (Write-Audit-Publish)** pattern.

## How It Works

### 1. Ingestion (EL)
*   **Tool:** `dlt`
*   **Source:** `src/etl/dlt_pipeline/`
*   **Action:** Scrapes daily price updates.
*   **Destination:** AWS S3 (Bronze Layer).
*   **Resilience:** Uses `tenacity` for retries and smart timeouts to handle intermittent server availability.

### 2. Transformation (T)
*   **Tool:** `dbt` (Data Build Tool) + DuckDB
*   **Source:** `src/etl/dbt_project/`
*   **Action:** 
    *   Reads Bronze data from S3.
    *   Transforms data to Silver and Gold layers.
*   **Quality Gate:** `dbt test` runs immediately after valid models are built. If any data quality test (e.g., price < 0 or price > 5000) fails, the pipeline stops.

### 3. Orchestration & Alerting
*   **Script:** `scripts/run_pipeline.py`
*   **Pattern:** **WAP (Write-Audit-Publish)**. 
    1.  **Preflight:** Verifies S3 connectivity.
    2.  **Write:** `dlt` runs extraction.
    3.  **Audit:** `dbt build` runs transformations and tests.
    4.  **Publish:** Data is ready for consumption.
*   **Alerting:** Sends real-time success/failure notifications to Discord via Webhook.

## Folder Structure

```
├── .github/workflows/    # CI/CD: Daily ingestion schedule (daily_run.yml)
├── script/               # Orchestration & Utility scripts
│   ├── run_pipeline.py   # Main entry point for ELT
│   ├── preflight_check.py# Verifies S3 connectivity
│   └── rebuild_lakehouse.py # Manual backfill tool
├── src/
│   ├── core/             # Shared utilities (logging, config)
│   ├── dashboard/        # Streamlit Application
│   │   ├── components/   # UI widgets (charts, filters)
│   │   └── utils/        # Data Engine (DuckDB S3 connector)
│   ├── etl/
│   │   ├── dlt_pipeline/ # Extraction logic (scrapers)
│   │   └── dbt_project/  # Transformation logic (SQL models)
└── .env                  # Local secrets (Not committed)
```

## Setup & Configuration

### Prerequisites
*   Python 3.12+
*   `uv` package manager

### Environment Variables (.env)
Create a `.env` file in the root directory:
```properties
# AWS Credentials (for S3 access)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-southeast-2
S3_BUCKET_NAME=...

# Alerting
DISCORD_WEBHOOK_URL=...
```

### Running Locally
1.  **Install dependencies:**
    ```bash
    uv sync
    ```
2.  **Run full pipeline:**
    ```bash
    uv run python scripts/run_pipeline.py
    ```
3.  **Launch Dashboard:**
    ```bash
    uv run python -m streamlit run src/dashboard/app.py
    ```
