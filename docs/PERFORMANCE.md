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
| **Total Runtime** | 42m 56s | *Pending Run* | -- |
| **NCR Duration** | ~5m | *Pending Run* | -- |
| **Throughput** | ~60 rows/min | TBD | -- |

> "The conveyor belt is now running 5 lanes wide."
