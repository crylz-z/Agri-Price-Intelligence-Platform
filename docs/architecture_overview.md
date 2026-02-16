# Agri-Price Intelligence Platform: Architecture Overview

This document acts as the definitive guide to the system architecture as of Phase 6.

## 1. High-Level Architecture

The platform follows a **Modern Data Stack (MDS)** approach, optimized for local execution but cloud-ready. It uses an **ELT (Extract, Load, Transform)** pattern with a localized Silver Layer.

### Core Stack
*   **Language**: Python 3.12+
*   **Orchestration**: Custom sequential pipeline (Extract -> Transform -> Audit)
*   **Compute (ETL)**: `concurrent.futures` (hreading), `pandas`, `duckdb` (SQL-on-files)
*   **Compute (Serving)**: `duckdb` (OLAP), `streamlit` (Frontend)
*   **Storage**: Local Filesystem (CSV for Raw, Parquet for Silver)
*   **Observability**: `structlog` (JSON logs), Discord Webhooks (Alerts)

---

## 2. Data Pipeline (The Engine)

### 2.1 Extraction Layer (`src/etl/extract/extract_data.py`)
*   **Goal**: Rapidly acquire data from DA Bantay Presyo while handling network flakes.
*   **Mechanism**:
    *   **Resilience**: Uses `tenacity` for exponential backoff retries on HTTP requests.
    *   **Concurrency**: `ThreadPoolExecutor` with 5 workers allows parallel region extraction.
    *   **Circuit Breaker**: If a region fails repeatedly, it logs an error, sends a **Discord Alert**, and returns a partial/failed state without crashing the whole pipeline.
*   **Output (Bronze)**: 
    *   Path: `data/raw/{YYYY-MM-DD}/prices_{REGION_NAME}_{TIMESTAMP}.csv`
    *   Format: Raw CSV (Immutable logic - we never overwrite, only append new files with timestamps).

### 2.2 Transformation Layer (`src/etl/transform/clean_data.py`)
*   **Goal**: Convert messy raw strings into typed, analytics-ready data.
*   **Processes**:
    1.  **Schema Validation**: Uses `pandera` to enforce data contracts (e.g., Price must be float, Market Name must not be null).
    2.  **DLQ Routing**: Rows/Files failing validation are immediately moved to `data/dlq/` (Dead Letter Queue) for manual inspection, ensuring the main pipeline stays pure.
    3.  **Deduplication (DuckDB)**: 
        *   Generates a `record_id` (MD5 hash of business keys).
        *   Uses DuckDB SQL window functions (`ROW_NUMBER()`) to implement a "Last-Write-Wins" strategy within the batch.
*   **Output (Silver)**:
    *   Path: `data/clean/date={YYYY-MM-DD}/market_prices.parquet`
    *   Format: Snappy-compressed Parquet, Hive-partitioned by Date.

### 2.3 Storage Layer (`src/core/io_manager.py`)
*   **Abstraction**: Centralized class to handle reading/writing, ensuring consistent path enforcement (`data/raw` vs `data/clean`).
*   **Efficiency**: Parquet reduces disk usage by ~90% compared to CSV and speeds up read times for the dashboard by ~50x.

---

## 3. Dashboard Architecture (`src/dashboard/`)

The dashboard is built on **Streamlit** but uses an **OLAP Engine Pattern** to simulate a real database.

### 3.1 Data Engine (`src/dashboard/utils/data_engine.py`)
Instead of loading all Parquet files into Pandas (RAM killer), we use **DuckDB** to query the Parquet files directly on disk.

*   **OLAP Querying**: 
    *   `SELECT * FROM read_parquet('data/clean/**/*.parquet') WHERE ...`
    *   This allows us to handle months of data with minimal RAM footprint.
*   **LKGV Strategy (Last Known Good Value)**:
    *   Govt data often has gaps (e.g., no report on Sunday).
    *   The Engine implements a "Window Lookback" (default 3 days). If data is missing for today, it automatically fetches the most recent price from the last 3 days to ensure the dashboard rarely shows "No Data".
*   **Geospatial Resilience**:
    *   Joins market names with `data/reference/markets_geo.csv`.
    *   **Fallback**: If a market reference is missing, it falls back to the *Region Center* coordinates and adds random "jitter" (1-2km) so points don't stack perfectly on top of each other.

### 3.2 UI Components
*   **Executive Brief**: High-level KPIs and Volatility warnings.
*   **Official Bulletin**: Table comparing Live Prices vs SRP (Suggested Retail Price).
*   **Fairness Meter**: Z-Score formulation to detect price gouging (outliers).
*   **Maps**: Folium integration for spatial context.

---

## 4. Security & Ops

*   **Configuration**: All secrets (Discord URL) managed via `.env` (gitignored).
*   **Logging**: Structured JSON logging to `logs/` for machine-readability.
*   **Alerting**: Critical failures trigger real-time Discord notifications.

## 5. Data Model

| Layer | Type | Granularity | Schema Key Fields |
| :--- | :--- | :--- | :--- |
| **Raw** | CSV | Transactional | `extract_dt`, `region_id`, `market`, `commodity`, `price_str` |
| **Clean** | Parquet | Daily Snapshot | `extract_dt` (Date), `region_name`, `market_name`, `commodity`, `price` (Float), `record_id` |
| **Ref** | CSV | Static | `market_name`, `lat`, `lon` |
