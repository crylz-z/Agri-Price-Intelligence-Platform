# Architecture Decision Records (ADR) - Agri-Price Intelligence Platform

## Executive Summary
This document outlines the architectural strategy and engineering trade-offs for the Agri-Price Intelligence Platform. The system is designed to provide enterprise-grade market surveillance through an automated, idempotent ELT pipeline and a high-performance analytical dashboard.

---

## Overall Architecture: The Medallion Lakehouse
The platform implements a **Medallion Architecture** on an S3-based Data Lake, ensuring data quality and lineage at every stage.

1.  **Bronze (Raw)**: Unprocessed multi-format extracts (JSON, CSV) from the DA Bantay Presyo source.
2.  **Silver (Cleaned)**: Parquet files with enforced schemas, normalized naming conventions, and initial outlier filtering.
3.  **Gold (Analytical)**: Flattened, high-performance views optimized for dashboard consumption (SQL and Parquet).

---

## Technical Stack & Rationale

### 1. Data Extraction & Loading: dlt (Data Load Tool)
*   **Why**: We chose `dlt` for its built-in handling of schema evolution, nested structures, and robust handling of API/Web-source failures. It enables a "Write-Audit-Publish" (WAP) pattern by landing data into the Bronze layer before downstream processing.

### 2. Transformation & Auditing: dbt (Data Build Tool)
*   **Why**: `dbt` is our transformation engine. It allows us to treat SQL as code, enabling version control, environment management, and—most importantly—automated data testing.
*   **Audit Logic**: Before data moves from Silver to Gold, `dbt test` validates that price distributions are within expected ranges, preventing corrupted data from reaching stakeholders.

### 3. Compute Engine: DuckDB
*   **Why**: DuckDB serves as our OLAP engine. Unlike Pandas, which requires loading massive datasets into RAM, DuckDB executes vectorized SQL directly against S3 Parquet files via the `httpfs` extension. This ensures the dashboard remains responsive even as the historical dataset grows into the gigabyte range.

### 4. Storage & Partitioning: AWS S3
*   **Why**: S3 provides virtually infinite, low-cost storage. We utilize strictly enforced **Hive-style partitioning** (`year=YYYY/month=MM/day=DD`).
*   **Trade-off**: This prevents expensive full-table scans. When the dashboard requests "Rice" prices for a specific week, DuckDB only reads the relevant S3 prefixes.

### 5. Resilience & Orchestration: Tenacity & GitHub Actions
*   **Why**: Web scraping is inherently brittle. We use `tenacity` for exponential backoff retries when the DA Bantay Presyo server is under load. Orchestration via GitHub Actions ensures daily idempotent execution without maintaining dedicated infrastructure.

### 6. Observability: Structlog
*   **Why**: Enterprise logs must be structured and machine-readable. `structlog` provides JSON-formatted output which can be easily ingested by cloud watchlogs or generic ELK stacks for pipeline monitoring and audit trails.

### 7. Spatial Analytics: Geopy & Nominatim
*   **Why**: Accurate market positioning is critical for identifying regional supply shocks. We use `geopy` to resolve text-based market names into precise coordinates via the OpenStreetMap Nominatim API.

---

## Visual Intelligence: Page-by-Page Logic

### Page 1: Regional Deep Dive
*   **Objective**: Granite-level market monitoring within a specific administrative region.
*   **Charts & Rationale**:
    *   **Market Map (Folium)**: Geocoded Pins (Teal for Cheap, Coral for Expensive). *Why*: Spatial visualization immediately identifies supply-chain bottlenecks or localized price hikes.
    *   **Category Substitutes (Altair)**: Displays prices of alternative commodities in the same category. *Why*: Helps users identify cheaper alternatives (e.g., swapping one rice variety for another) when a specific commodity spikes.
    *   **Historical Baseline Delta**: Compares current prices to a 30-day statistical mean. *Why*: Provides context on whether a price is seasonally normal or an outlier.
    *   **Price Fairness Index (Z-Score)**: Ranks markets by their distance from the regional mean. *Why*: Mathematically identifies "Price Gouging" (Z-Score > 1.5).

### Page 2: National Macro Watch
*   **Objective**: Cross-regional comparison to identify macro-economic disparities.
*   **Charts & Rationale**:
    *   **Regional Price Ranking**: A national leaderboard of regional averages. *Why*: Identifies which regions are currently underserved or experiencing supply shocks.
    *   **National Insight Banner**: Identifies the cheapest and most expensive regions nationwide. *Why*: Surfaces the "Price Spread" at a federal level.

### Page 3: Historical Trends
*   **Objective**: Advanced temporal pattern recognition.
*   **Charts & Rationale**:
    *   **Price Volatility Envelope**: Shaded Slate area (Min-Max) with a solid Teal line (Mean). *Why*: Aggregates thousands of data points into a single "Trend Corridor" to resolve visual noise (barcode artifacts).
    *   **Day-of-Week Price Intensity Matrix (Heatmap)**: Maps days vs. weeks using Sequential Coral colors. *Why*: Surfaces "Cheap Days" vs. "Expensive Days" across the month, enabling strategic procurement timing.

---

## Security & Operations
*   **Zero-Secrets Policy**: All AWS credentials and webhooks are managed via `.env` files (locally) or GitHub Secrets (CI/CD).
*   **Idempotent Scheduling**: GitHub Actions run 3 times per day at specific UTC windows (04:00, 09:00, 12:30). Each run is idempotent; if a run fails, the subsequent window safely recovers.
