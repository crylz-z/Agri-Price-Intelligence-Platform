# Architecture Reference Document (ARD)

## 1. Executive Summary
The **Agri-Price Intelligence Platform** is a serverless, event-driven data pipeline designed to extract, transform, and analyze agricultural price data from government sources. Ideally, it avoids "duct-tape" solutions by strictly adhering to an **ELT (Extract-Load-Transform)** pattern using **DuckDB** and **S3**.

## 2. Key Architecture Decisions (ADRs)

### ADR-001: Cloud-Native ELT over ETL
- **Decision**: We extract raw data and load it immediately into S3 (Bronze) before any transformation.
- **Why**: Allows re-processing of historical data if business logic changes. Decouples extraction failures from transformation logic.

### ADR-002: Serverless Compute (GitHub Actions)
- **Decision**: The entire pipeline runs ephemeral runners on GitHub Actions.
- **Why**: Zero infrastructure cost for idle time. Fits the batch nature (3x/day) of the workload perfectly.

### ADR-003: In-Process OLAP (DuckDB)
- **Decision**: Use DuckDB instead of Spark/Databricks or Postgres.
- **Why**:
    - **Cost**: Free (runs on the runner).
    - **Speed**: Vectorized execution on Parquet files is significantly faster than row-based databases.
    - **Simplicity**: No separate database server to manage/secure.

### ADR-004: Security via OIDC
- **Decision**: Use AWS OpenID Connect (OIDC) for GitHub Actions authentication.
- **Why**: Eliminates long-lived AWS Access Keys. GitHub requests a temporary token from AWS IAM for the duration of the job only.

## 3. Data Lake Architecture

| Layer | Format | Location | Description |
| :--- | :--- | :--- | :--- |
| **Bronze** | JSON/CSV | `s3://.../bronze/` | Raw data as received from source. Partitioned by `extract_dt`. |
| **Silver** | Parquet | `s3://.../silver/` | Cleaned, deduplicated, type-cast data. |
| **Gold** | Parquet | `s3://.../gold/` | Aggregated metrics (Volatility, Daily Averages). |

## 4. Operational Strategy & Developer Workflow

### Faster Feedback Loops
The 1-hour cron schedule is too slow for development. To test changes immediately:
1.  **Manual Trigger**: Go to GitHub Actions -> Select "Daily Price Extraction" -> Click "Run workflow". This starts in ~30 seconds.
2.  **Local Testing**:
    - **Constraints**: You cannot use OIDC locally. You must have local `~/.aws/credentials` or `AWS_ACCESS_KEY_ID` env vars set.
    - **Command**: `python scripts/preflight_check.py` (Tests S3 connectivity).
    - **Command**: `python -m src.etl.extract.extract_data` (Runs extraction logic).

## 5. Technology Stack
- **Orchestration**: GitHub Actions
- **Compute**: Ubuntu Runners (Standard)
- **Storage**: AWS S3
- **Database/Engine**: DuckDB
- **Language**: Python 3.12 (uv for package management)
