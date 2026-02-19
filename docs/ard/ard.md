# Architecture Decision Record (ARD)

## ADR-001: Cloud-Native ELT with DuckDB and S3

### Context
The project requires a cost-effective, scalable, and maintainable data pipeline to ingest agricultural price data, transform it, and serve it to a dashboard. Traditional warehouses (Snowflake, BigQuery) introduce recurring costs and latency overhead for this scale.

### Decision
We adopted a **Serverless Lakehouse** architecture using:
1.  **Extraction:** `dlt` (Data Load Tool) for robust python-based scraping.
2.  **Storage:** AWS S3 as the content-addressable storage layer (Bronze/Silver/Gold Parquet files).
3.  **Compute:** DuckDB (In-process OLAP) for both transformation (`dbt-duckdb`) and serving (Streamlit).
4.  **Orchestration:** GitHub Actions + Python script acting as a lightweight DAG runner.

### Rationale

#### 1. Decoupled Storage & Compute
By storing data in open Parquet format on S3, we avoid vendor lock-in. Compute is ephemeral (running only during GitHub Actions or Streamlit sessions), reducing costs to near-zero when idle.

#### 2. In-Process processing (DuckDB)
DuckDB allows us to run complex SQL transformations directly on the runner/container without provisioning a database server. Its `httpfs` extension enables high-performance reads directly from S3 partitions.

#### 3. WAP Pattern (Write-Audit-Publish)
To prevent bad data from breaking the dashboard, we enforce a strict WAP pipeline:
*   **Write:** Data is extracted to a staging area.
*   **Audit:** `dbt test` validates constraints (e.g., price < 5000, valid regions).
*   **Publish:** Only if tests pass is the pipeline marked successful. The dashboard reads the validated Gold layer.

### Consequences
*   **Pros:** Extremely low cost, high performance for <10GB data, simple deployment (python-only).
*   **Cons:** Latency in S3 listing (mitigated by Hive Partitioning), concurrency limits (DuckDB is single-writer, but we only have one writer pipeline).
