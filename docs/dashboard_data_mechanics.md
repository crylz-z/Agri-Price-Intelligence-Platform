# Dashboard Data Mechanics & Logic Deep Dive

This document explains **exactly** how the dashboard transforms raw files into the metrics you see on screen. It covers the Data Pipeline, The "LKGV" Strategy, and the Mathematical Formulas used.

---

## 1. The "Database" (File-Based Storage)

The dashboard does **not** connect to a traditional SQL database (like PostgreSQL or MySQL). Instead, it uses a **Data Lake** architecture where the "database" is simply a collection of files in your `data/` folder.

| Layer | Path | Format | Purpose |
| :--- | :--- | :--- | :--- |
| **Raw Layer** | `data/raw/YYYY-MM-DD/` | `.csv` | The original, untouched scrape data. |
| **Clean Layer** | `data/clean/` | `.parquet` | Optimized, compressed, and standardized data. This is what the dashboard reads. |
| **Reference** | `data/reference/` | `.csv` | Static lookup tables (SRP, Locations). |

### Why Parquet?
The dashboard reads `.parquet` files instead of `.csv` because:
1.  **Speed**: It is 10-50x faster to read.
2.  **Types**: It preserves data types (e.g., it knows `price` is a number, not a string).

---

## 2. The Loading Strategy: "LKGV" (Last Known Good Value)

The dashboard does not just show "today's data" because real-world scraping is messy—sometimes a market is closed, or the government server is down.

To fix this, the dashboard uses the **LKGV Windowing Strategy**.

### How it Works (The Algorithm):
1.  **The Window**: When you select a date (e.g., `Feb 14`), the system actually loads data for `Feb 14`, `Feb 13`, and `Feb 12` (Window Size = 3 Days).
2.  **The Stack**: It stacks these days on top of each other.
3.  **The Squash (Coalesce)**: It sorts them by date (Newest First) and removes duplicates based on the "Natural Key": `(Region + Market + Commodity)`.

**The Result:**
*   If `Market A` has data for `Feb 14`, you see that price.
*   If `Market A` failed to report on `Feb 14`, the dashboard automatically SHOWS you the price from `Feb 13`, but flags it as locally "stale" (Yesterday).

> **Business Value:** This prevents the dashboard from looking broken/empty just because of a minor partial failure in data collection.

---

## 3. Reference Data Sources

The "Official" data comes from static CSV files you control.

### A. The Price Targets (SRP)
*   **Source:** `data/reference/official_srp.csv`
*   **Columns:** `category`, `commodity`, `official_srp`
*   **Usage:** This is the "Gold Standard". The dashboard compares every live price against this number to determine if a price is "High", "Low", or "Fair".

### B. The Map Locations (Geo)
*   **Source:** `data/reference/markets_geo.csv`
*   **Columns:** `market_name`, `lat`, `lon`
*   **Usage:** The dashboard uses the `market_name` to look up the GPS coordinates.
*   **Limitation:** If a market name in the scrape (e.g., "Pasig Mega Market") does not *exactly* match the name in this CSV, it will not appear on the map.

---

## 4. The Math: Formulas & Calculations

Here is exactly how the charts and metrics are calculated.

### A. "Staleness" (Days Ago)
Calculated dynamicially for every row:
```python
Days Ago = (Selected Date) - (Extraction Date of the Row)
```
*   `0` = Today (Fresh)
*   `>0` = Stale (Data from previous days in the window)

### B. "Fairness Meter" (Z-Score)
This chart tells you **how unusual** a price is compared to the *current market average* (not the SRP).

**The Formula:**
```math
Z = (Price - Average) / Standard Deviation
```

*   **Average**: The mean price of that commodity across ALL markets today.
*   **Std Dev**: A measure of how "spread out" the prices are.
*   **Interpretation**:
    *   `Z > 0` (Red Bar): This market is **more expensive** than the average.
    *   `Z < 0` (Green Bar): This market is **cheaper** than the average.
    *   `Length of Bar`: How extreme the difference is.

### C. "Variance" (vs SRP)
This simple subtraction tells you the raw peso difference from the government target.
```math
Variance = (Live Price) - (Official SRP)
```

### D. "Volatility" (Executive Brief)
A percentage score that tells you how chaotic the market is right now.
```math
Volatility % = ((Max Price - Min Price) / Average Price) * 100
```
*   **> 20%**: Crisis/Chaos (Red Warning)
*   **< 10%**: Stable (Green Success)

---

## 5. Summary of Data Flow

1.  **User** selects Date/Region/Category.
2.  **Loader** grabs the last 3 days of Parquet files `data/clean/*.parquet`.
3.  **Engine** stacks them and keeps only the newest record for every market-commodity pair.
4.  **Enricher** joins this data with `official_srp.csv` (for targets) and `markets_geo.csv` (for map pins).
5.  **Visualizer** computes the math (Z-Score, Volatility) and renders the charts.
