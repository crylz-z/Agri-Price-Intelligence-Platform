# Philippine Agri-Price Intelligence Platform (APIP) 🌾

> **"A Time Machine for Food Prices"**
> An automated data pipeline that captures, validates, and archives daily agricultural price data from the Department of Agriculture, enabling real-time inflation monitoring and arbitrage detection.

![Python](https://img.shields.io/badge/Python-3.9-blue) ![GitHub Actions](https://img.shields.io/badge/Automation-GitHub_Actions-green) ![Data](https://img.shields.io/badge/Data-Parquet%2FCSV-orange)

## 🚀 The Problem
The government price monitoring website is ephemeral. Data is updated daily, and historical data is deleted. This creates "Information Asymmetry" where market variances (e.g., ₱50 Corn vs ₱80 Corn) are hidden from consumers and businesses.

## 🛠️ The Solution
This project implements a **Serverless Data Pipeline** ("The Robot") that:
1.  **Extracts**: Scrapes granular price data for 10+ commodities (Rice, Meat, Fish, Veggies) from the DA API.
2.  **Validates**: Applies a "Hybrid Validation" logic to ensure data accuracy (rejects >15% variance).
3.  **Loads**: Archives clean, structured data (CSV/Parquet) for historical analysis.
4.  **Automates**: Runs bit-perfectly every day at 6:00 AM, 12:00 PM, and 6:00 PM via **GitHub Actions** (Git Scraping pattern).

## 📂 Project Structure
```bash
├── config/             # The "Recipe Book"
│   └── settings.py     # Centralized configuration (URLs, Commodity IDs)
├── data/               # The "Pantry"
│   └── raw/            # Daily price snapshots (Commited automatically)
├── logs/               # The "Security Camera"
│   └── extraction.log  # Execution history (GitIgnored)
├── src/                # The "Chefs"
│   └── daily_extraction.py # Master ETL script
├── tests/              # The "Health Inspector"
│   └── health_check.py # Data integrity verifier
└── .github/workflows/  # The "Alarm Clock"
    └── daily_run.yml   # Multi-pass scheduling logic
```

## 💻 Tech Stack
*   **Ingestion**: Python (`requests`, `BeautifulSoup`, `pandas`)
*   **Orchestration**: GitHub Actions (Cron Schedule)
*   **Storage**: Git Repository (Zero-Cost Data Lake)
*   **Quality**: Custom Validation Logic

## 🏃 How to Run Locally
1.  **Clone the Repo**:
    ```bash
    git clone https://github.com/crylz-z/Agri-Price-Intelligence-Platform.git
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Robot**:
    ```bash
    python src/daily_extraction.py
    ```

## 📈 Impact
*   **For Consumers**: Identifies the cheapest wet market in NCR for specific goods.
*   **For Businesses**: Enables data-driven procurement to reduce costs by 15-20%.
*   **For the Market**: Exposes predatory pricing and encourages fair competition.

---
*Built by [Your Name] as a showcase of modern Data Engineering patterns.*
