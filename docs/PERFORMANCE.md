# System Performance & Optimizations

## 1. Storage Optimization (Parquet)
We migrated the storage backend from standard CSV to **Apache Parquet**.
*   **Compression**: Snappy.
*   **Rationale**: The text-heavy nature of the dataset (Market Names, Commodities) compresses highly efficiently.
*   **Metrics**:
    *   **CSV Size**: ~15MB / month
    *   **Parquet Size**: ~1.5MB / month
    *   **Reduction**: ~90%

## 2. Ingestion Concurrency
The extraction engine utilizes `concurrent.futures.ThreadPoolExecutor`.
*   **Configuration**: 5 Workers.
*   **Throughput**: The system processes 170 requests in approximately 45-60 seconds.
*   **Constraint**: Rate-limiting is self-imposed (0.5s delay) to respect the host server's capacity and prevent IP bans.

## 3. Dashboard Latency
Streamlit's reactive model can introduce latency with large datasets.
*   **Caching**: We utilize `@st.cache_data` with a TTL (Time-to-Live) of 4 hours.
*   **Lazy Loading**: Historical metrics are computed only when the "Strategic View" page is loaded, keeping the main "National Market Watch" page lightweight.
*   **Vectorized Operations**: All aggregations (Mean, Min, Max) utilize native Pandas C-optimized vectorization rather than Python loops.

## 4. Resilience
*   **Audit Log**: The `audit_log.txt` is a lightweight semaphore file (size: <100 bytes). It eliminates the need for a database query to determine system health during CI/CD checks.
