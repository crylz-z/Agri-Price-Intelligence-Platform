# Pipeline Performance & Optimization Log

## 1. Baseline (The "Slow" Run)
*   **Date**: Feb 11, 2026
*   **Strategy**: Sequential Loop (Synchronous)
*   **Total Runtime**: 42m 56s
*   **Bottleneck**: Region III (Central Luzon) timeouts blocked all subsequent regions.
*   **Observation**: The scraper processes one region at a time. If one hangs, the whole pipeline stalls.

## 2. Optimization Strategy (The Solution)
*   **Technique**: Implemented `ThreadPoolExecutor` with **5 concurrent workers**.
*   **Hypothesis**: Parallelism will isolate slow regions (timeouts) allowing fast regions to complete independently.
*   **Safety**: Using a maximum of 5 workers to avoid overloading the source API.

## 3. Results
| Metric | Baseline (Sequential) | Optimized (Parallel) | Improvement |
| :--- | :--- | :--- | :--- |
| **Total Runtime** | 42m 56s | **31m 00s** | **26% faster** |
| **NCR Duration** | ~5m | ~3m | -- |
| **Throughput** | ~60 rows/min | ~80 rows/min | -- |


## 4. Optimization Round 2 (The "Speed Run")
*   **Technique**: Implemented `requests.Session()` with `HTTPAdapter` and Aggressive Timeouts (10s).
*   **Hypothesis**: Lowering the TCP/SSL overhead and failing fast on dead connections will cut runtime by another 50%.
*   **Changes**:
    *   Replaced `requests.post()` with `session.post()`.
    *   Mounted `HTTPAdapter` for socket-level retries.
    *   Reduced timeout from 30s to 10s.

> "Dial once, talk fast."
