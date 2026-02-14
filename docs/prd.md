# Product Requirement Document (PRD)

**Project**: Agri-Price Intelligence Platform (APIP)
**Version**: 3.0
**Status**: Stable / Feature Freeze

## 1. Executive Summary
The Agri-Price Intelligence Platform (APIP) is an automated data pipeline and decision support system designed to capture, validate, and visualize daily agricultural price data from the Department of Agriculture (Bantay Presyo). It addresses the critical issue of "Information Asymmetry" in the agricultural market by providing a persistent, historical record of price fluctuations that is otherwise unavailable through government portals.

## 2. Core Architecture

### 2.1 The Matrix Strategy (Ingestion)
To overcome the limitations of the source API (which does not support bulk data export), we implemented a "Matrix Strategy."
*   **Concept**: Iterate through the Cartesian product of all available Regions (17) and Commodity Categories (10).
*   **Execution**: The extraction engine concurrently requests data for each `(Region, Category)` pair.
*   **Result**: 170 distinct data vectors are harvested daily, ensuring 100% coverage of the available dataset.

### 2.2 Content-Based Routing (Normalization)
The source API exhibits a "Midnight Bug" where data requests made shortly after midnight may return the previous day's data with an incorrect date label, or vice versa.
*   **Solution**: The pipeline inspects the actual date embedded within the HTML payload (`data-date` attribute) rather than relying on the request timestamp.
*   **Outcome**: Data is correctly attributed to its true source date, preventing data corruption during temporal boundaries.

### 2.3 The Silver Layer (Transformation)
Raw data is notoriously messy (formatting inconsistencies, missing fields).
*   **Process**: All raw CSV extracts are processed through a strict cleaning layer.
    *   **Normalization**: Column names to `snake_case`. Strings to `Title Case`.
    *   **Typing**: Numeric coercions for prices.
    *   **Enrichment**: Region IDs are mapped to human-readable names.
*   **Storage**: Validated data is serialized into **Parquet** format using Snappy compression. This reduces storage requirements by approximately 90% compared to CSV and significantly improves read performance for the dashboard.

### 2.4 The Bouncer (Audit Mechanism)
To prevent the dashboard from displaying incomplete data, an automated audit gate ("The Bouncer") is enforced.
*   **Logic**: A scrape is considered "Failed" if it returns fewer than 500 records or covers fewer than 10 regions.
*   **Action**: Failed scrapes differ `audit_log.txt` to a "FAIL" state, which signals the GitHub Action/Deployment pipeline to halt.
*   **Persistence**: `audit_log.txt` serves as the persistent state file, allowing the system to verify the health of the last data ingress without re-analyzing the entire dataset.

## 3. Dashboard Specifications

### 3.1 National Market Watch (Tactical View)
*   **Goal**: Operational awareness.
*   **Key Features**:
    *   **Best Deal Engine**:  Identifies the lowest price for a specific commodity within a selected region.
    *   **Gouging Alert**: Flags markets charging >15% above the regional average or SRP.
    *   **Geospatial Map**: Pins market locations for logistical planning.

### 3.2 Historical Trends (Strategic View)
*   **Goal**: Long-term pattern analysis.
*   **Key Features**:
    *   **Volatility Index**: Visualizes the daily price spread (Min vs. Max) to identify market instability.
    *   **Trajectory**: Multi-line chart tracking price movement over 30-90 days across different markets.

## 4. Security
*   **Secret Management**: Configuration is code-based; no external API keys are required.
*   **Data Isolation**: Raw ingestion data (Bronze) is strictly separated from Dashboard-ready data (Silver).
