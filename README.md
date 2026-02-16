# Agri-Price Intelligence Platform

## Architecture Overview
The Agri-Price Intelligence Platform employs a Medallion Lakehouse architecture to ingest, process, and analyze agricultural commodity price data.

-   **Bronze Layer**: Raw data ingestion from source APIs (AWS S3).
-   **Silver Layer**: Cleaned, deduplicated, and enriched data (DuckDB + Parquet).
-   **Gold Layer**: Aggregated metrics and business-level analytics (DuckDB + Parquet).

## Technology Stack
-   **Core Runtime**: Python 3.12
-   **Package Management**: `uv`
-   **Data Processing**: DuckDB (In-process OLAP), `httpfs`
-   **Storage**: AWS S3 (Hive Partitioning)
-   **CI/CD**: GitHub Actions
-   **Orchestration**: Scheduled Workflows (Triple Tap: 02:00, 06:00, 10:00 UTC)

## Folder Structure
```
├── config/             # Environment and application configuration
├── data/               # Local data storage (mapped to S3 structure)
├── docs/               # Project documentation
├── scripts/            # Utility and backfill scripts
├── src/
│   ├── core/           # Shared utilities (logging, http_client)
│   ├── etl/            # Extract-Transform-Load pipelines
│   └── visualization/  # Dashboard and reporting components
├── tests/              # Unit and integration tests
├── .github/            # CI/CD workflow definitions
├── .agent/             # AI Agent context and artifacts
└── pyproject.toml      # Dependency and project metadata
```

## Local Setup

### Prerequisites
-   Python 3.12+
-   `uv` package manager

### Installation
1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd agri-price-intelligence-platform
    ```

2.  Install dependencies:
    ```bash
    uv sync
    ```

3.  Configure Environment:
    Copy `.env.example` to `.env` and populate AWS credentials.
    ```bash
    cp .env.example .env
    ```

### Execution
Run the full ETL pipeline locally:
```bash
python -m src.etl.extract.extract_data
python -m src.etl.transform.clean_data
```
