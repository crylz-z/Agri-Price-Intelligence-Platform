# Agri-Price Intelligence Platform

## System Architecture

The platform uses a modern **ELT (Extract, Load, Transform)** architecture orchestrated by GitHub Actions and monitored via Discord.

```mermaid
graph TD
    subgraph Sources
        A[DA-AMAS Website]
    end

    subgraph "Data Lake (S3)"
        B[Bronze Layer<br>(Raw Parquet)]
        C[Silver Layer<br>(Cleaned Parquet)]
        D[Gold Layer<br>(Aggregated Parquet)]
    end

    subgraph Processing
        E[dlt Pipeline<br>(Extract & Load)]
        F[dbt Core<br>(Transform & Test)]
    end

    subgraph Consumption
        G[Streamlit Dashboard]
        H[Ad-hoc Analysis<br>(DuckDB)]
    end

    subgraph Orchestration
        I[GitHub Actions<br>(Daily Schedule)]
        J[Orchestrator Script<br>(run_pipeline.py)]
        K[Discord Webhook<br>(Alerting)]
    end

    I --> J
    J -->|Step 1: Extract| E
    E -->|Scrape| A
    E -->|Write| B
    
    J -->|Step 2: Transform| F
    B -->|Read| F
    F -->|Materialize| C
    F -->|Materialize| D
    
    C -->|Read| G
    D -->|Read| G
    D -->|Read| H
    
    J -->|On Success/Fail| K
```

## How It Works

### 1. Ingestion (EL)
*   **Tool:** `dlt` (Data Load Tool)
*   **Source:** `src/etl/dlt_pipeline/`
*   **Action:** Scrapes daily price updates from the DA-AMAS website.
*   **Destination:** Writes raw data to AWS S3 (Bronze Layer) as partitioned Parquet files.
*   **Resilience:** Uses `tenacity` for retries and smart timeouts to handle slow government servers.

### 2. Transformation (T)
*   **Tool:** `dbt` (Data Build Tool) + DuckDB
*   **Source:** `src/etl/dbt_project/`
*   **Action:** 
    *   Reads Bronze data directly from S3.
    *   Cleans, dedupes, and standardizes schema (Silver).
    *   Aggregates metrics for the dashboard (Gold).
*   **Quality Gate:** `dbt test` runs immediately after valid models are built. If any data quality test (e.g., price < 0 or price > 5000) fails, the pipeline stops.

### 3. Orchestration & Alerting
*   **Script:** `scripts/run_pipeline.py`
*   **Pattern:** **WAP (Write-Audit-Publish)**. 
    1.  **Write:** `dlt` runs.
    2.  **Audit:** `dbt build` runs (models + tests).
    3.  **Publish:** If successful, data is ready for the dashboard.
*   **Alerting:** Sends real-time success/failure notifications to a Discord channel via Webhook.

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
S3_BUCKET_NAME=apip-data-lake-2026-crylz

# Alerting
DISCORD_WEBHOOK_URL=...
```

### Running Locally
1.  **Install dependencies:**
    ```bash
    uv sync
    ```
2.  **Test connection:**
    ```bash
    python max scripts/preflight_check.py
    ```
3.  **Run full pipeline:**
    ```bash
    python scripts/run_pipeline.py
    ```
4.  **Launch Dashboard:**
    ```bash
    uv run streamlit run src/dashboard/app.py
    ```
