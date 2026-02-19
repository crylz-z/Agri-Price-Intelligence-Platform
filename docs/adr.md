# Architecture Overview: Serverless Lakehouse

**Date:** 2026-02-19
**Status:** Accepted

## Executive Summary
This document outlines the architectural decisions behind the Agri-Price Intelligence Platform. The system utilizes a **Serverless Lakehouse** architecture, leveraging AWS S3 for storage and DuckDB for compute. This approach was selected to minimize operational costs, eliminate infrastructure management, and prevent vendor lock-in, while maintaining rigorous data engineering standards.

## Problem Statement
The platform ingests agricultural price data from government sources that publish irregularly. The data volume is moderate (thousands of records), but the value is derived from historical trend analysis and timely alerting.

Traditional data warehousing solutions were evaluated and rejected:
*   **Relational Databases (RDS/Postgres):** Incur 24/7 costs for a pipeline that runs only a few times daily.
*   **Cloud Warehouses (Snowflake/BigQuery):** Minimum credit usage and storage costs are disproportionate to the data volume.
*   **Operational Overhead:** Both options require user management, network security configuration, and ongoing maintenance.

## Solution Architecture

### 1. Storage Layer: AWS S3
S3 serves as the primary data store. Data is persisted as **Parquet** files, a columnar format optimized for analytical querying and high compression.
*   **Benefit:** Decouples storage from compute. Storage costs are negligible and based strictly on usage.
*   **Lock-in:** Eliminates vendor lock-in; data remains in an open standard format accessible by any tool.

### 2. Compute Engine: DuckDB
DuckDB is utilized as an in-process analytical engine. It executes SQL transformations directly on the runner environment without requiring a persistent database server.
*   **Capability:** The `httpfs` extension allows DuckDB to query Parquet files directly from S3, treating the object store as a queryable database.
*   **Efficiency:** Compute is ephemeral. Resources are provisioned only during active pipeline execution (GitHub Actions) or user sessions (Streamlit).

### 3. Ingestion: dlt (Data Load Tool)
The `dlt` library manages data extraction. It handles schema inference, type coercion, and normalization automatically.
*   **Resilience:** Adapts to minor upstream schema changes without pipeline failure.
*   **Standardization:** Ensures data lands in the Bronze layer in a consistent, typed format.

### 4. Transformation & Quality: dbt (Data Build Tool)
Data transformation is treated as software code using `dbt`. The pipeline implements a **Write-Audit-Publish (WAP)** pattern:
1.  **Write:** Raw data is staged (Bronze).
2.  **Audit:** `dbt test` validates business logic (e.g., negative prices, invalid regions).
3.  **Publish:** Only validated data is promoted to the Gold layer for consumption.

### 5. Orchestration: GitHub Actions
The pipeline is orchestrated via GitHub Actions, utilizing an **Adaptive Schedule**:
*   **Scout Mode (12:00 PM / 5:00 PM):** Lightweight runs to detect early data publication.
*   **Harvester Mode (8:30 PM / 11:30 PM):** Comprehensive runs to ensure final data capture and recovery from upstream delays.

## Conclusion
This architecture delivers the capabilities of a modern data warehouse—ACID compliance, schema enforcement, and SQL interface—with the cost profile of static object storage. It is fully serverless; when idle, the only infrastructure cost is the S3 storage fee.
