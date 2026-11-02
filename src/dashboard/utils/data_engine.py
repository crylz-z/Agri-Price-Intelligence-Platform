import pandas as pd
import os
import duckdb
import streamlit as st
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import random
from dotenv import load_dotenv
from src.core import storage

# Load environment variables
load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
CLEAN_PATH = (
    f"s3://{S3_BUCKET}/clean/posting_date=*/prices.parquet" if S3_BUCKET else None
)
# Clean rows in the column shape the pages expect. `extract_dt` carries the DA
# posting date (the date the price is for); filter on posting_date to prune files.
PRICES = f"""(
    SELECT posting_date, region_name, market_name,
        commodity_group AS category, commodity_name AS commodity, price,
        CAST(posting_date AS TIMESTAMP) AS extract_dt
    FROM read_parquet('{CLEAN_PATH}', hive_partitioning=true)
)"""


# ==========================================
# CONFIGURATION
# ==========================================


# REGION CENTERS (Approximate Lat/Lon)
REGION_CENTERS = {
    "NCR (NATIONAL CAPITAL REGION)": (14.5995, 120.9842),
    "CAR (CORDILLERA ADMINISTRATIVE REGION)": (17.4136, 120.9575),
    "REGION I (ILOCOS REGION)": (16.0827, 120.4578),
    "REGION II (CAGAYAN VALLEY)": (16.9754, 121.8107),
    "REGION III (CENTRAL LUZON)": (15.4828, 120.7120),
    "REGION IV-A (CALABARZON)": (14.1008, 121.0794),
    "REGION IV-B (MIMAROPA)": (13.1428, 121.2276),
    "REGION V (BICOL REGION)": (13.4346, 123.4079),
    "REGION VI (WESTERN VISAYAS)": (10.7202, 122.5621),
    "REGION VII (CENTRAL VISAYAS)": (9.8169, 124.0641),
    "REGION VIII (EASTERN VISAYAS)": (11.2443, 125.0033),
    "REGION IX (ZAMBOANGA PENINSULA)": (7.8384, 122.4277),
    "REGION X (NORTHERN MINDANAO)": (8.2280, 124.2452),
    "REGION XI (DAVAO REGION)": (7.1907, 125.4553),
    "REGION XII (SOCCSKSARGEN)": (6.5063, 124.8483),
    "REGION XIII (Caraga)": (8.8142, 125.5905),
    "BARMM (Bangsamoro Autonomous Region of Muslim Mindanao)": (7.2245, 124.2687),
}


class DataEngine:
    """
    OLAP Data Engine for Dashboard.
    Uses DuckDB to query Parquet files directly from the clean layer on R2.
    """

    @staticmethod
    def _get_connection():
        """Returns a DuckDB connection configured for S3 access."""
        con = duckdb.connect(database=":memory:")

        bucket = os.getenv("S3_BUCKET_NAME")
        if not bucket:
            print("[ERROR] Missing S3_BUCKET_NAME in environment.")
            return con

        try:
            storage.configure_duckdb(con)
        except Exception as e:
            print(f"[ERROR] Failed to configure DuckDB S3: {e}")

        return con

    @staticmethod
    @st.cache_data(ttl=600)
    def get_market_snapshot(target_date_str, window_days=3, _cache_buster=2):
        """
        Loads the 'Last Known Good Value' (LKGV) snapshot for a specific date from the clean layer.
        """
        bucket = os.getenv("S3_BUCKET_NAME")
        if not bucket:
            return pd.DataFrame()

        try:
            date.fromisoformat(target_date_str)
            # 1. Retrieve absolute latest available date in S3 that is <= target_date
            # This ensures availability is not restricted by a fixed window during data gaps.
            con = DataEngine._get_connection()
            latest_available_query = f"""
                SELECT MAX(posting_date) as latest_dt
                FROM {PRICES}
                WHERE posting_date <= DATE '{target_date_str}'
            """
            latest_dt_df = con.sql(latest_available_query).df()

            if latest_dt_df.empty or pd.isnull(latest_dt_df.iloc[0]["latest_dt"]):
                con.close()
                return pd.DataFrame()

            lkgv_date = latest_dt_df.iloc[0]["latest_dt"]
            lkgv_date_str = lkgv_date.strftime("%Y-%m-%d")

            # 2. Load all records for the identified 'Last Known Good Date'
            # (clean already holds one row per market and commodity per date).
            query = f"""
            SELECT * EXCLUDE (posting_date)
            FROM {PRICES}
            WHERE posting_date = DATE '{lkgv_date_str}'
            """

            df = con.sql(query).df()
            con.close()

            if "price" in df.columns:
                df.rename(columns={"price": "Prevailing Price (₱)"}, inplace=True)

            # Filter price outliers (> 5x median + Hard Cap)
            if not df.empty and "Prevailing Price (₱)" in df.columns:
                # Force numeric
                df["Prevailing Price (₱)"] = pd.to_numeric(
                    df["Prevailing Price (₱)"], errors="coerce"
                )

                # Execute Hard Cap (20k PHP)
                df = df[df["Prevailing Price (₱)"] <= 20000]

                if not df.empty:
                    median_price = df["Prevailing Price (₱)"].median()
                    if median_price > 0:
                        df = df[df["Prevailing Price (₱)"] <= median_price * 5]

            # Calculate temporal offset (days_ago) for freshness tracking
            if not df.empty and "extract_dt" in df.columns:
                df["extract_dt"] = pd.to_datetime(df["extract_dt"], errors="coerce")
                target_dt = pd.to_datetime(target_date_str).date()
                df["days_ago"] = df["extract_dt"].apply(
                    lambda x: (target_dt - x.date()).days if pd.notnull(x) else 0
                )

            return df
        except Exception as e:
            print(f"[ERROR] Engine Error: {e}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_truth_df(target_date_str, region=None, category=None, commodity=None):
        """
        Retrieves a 'Single Source of Truth' DataFrame filtered by date and scope.
        Ensures mathematical consistency across all downstream dashboard components.
        """
        df = DataEngine.get_market_snapshot(target_date_str)
        if df.empty:
            return df

        if region:
            df = df[df["region_name"] == region]
        if category:
            df = df[df["category"] == category]
        if commodity:
            df = df[df["commodity"] == commodity]

        return df.copy()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_historical_trends(
        commodity, region, days_back=30, end_date_str=None, _cache_buster=1
    ):
        """
        Fetches time-series data for a commodity/region pair from the clean layer.
        """
        bucket = os.getenv("S3_BUCKET_NAME")
        if not bucket:
            return pd.DataFrame()

        today = datetime.now(ZoneInfo("Asia/Manila")).date()
        if end_date_str:
            try:
                end_date = date.fromisoformat(end_date_str)
            except Exception:
                end_date = today
        else:
            end_date = today

        start_date = end_date - timedelta(days=days_back)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_formatted = end_date.strftime("%Y-%m-%d")

        region_clause = f"AND region_name = '{region}'" if region else ""

        query = f"""
        SELECT
            extract_dt,
            price as 'Prevailing Price (₱)',
            region_name,
            market_name,
            commodity
        FROM {PRICES}
        WHERE
            posting_date BETWEEN DATE '{start_date_str}' AND DATE '{end_date_formatted}'
            AND commodity = '{commodity}'
            {region_clause}
        ORDER BY extract_dt ASC
        """

        try:
            con = DataEngine._get_connection()
            df = con.sql(query).df()
            con.close()

            if not df.empty:
                df["extract_dt"] = pd.to_datetime(
                    df["extract_dt"], format="mixed", errors="coerce"
                )

                if "Prevailing Price (₱)" in df.columns:
                    # Force numeric + Hard Cap 20k
                    df["Prevailing Price (₱)"] = pd.to_numeric(
                        df["Prevailing Price (₱)"], errors="coerce"
                    )
                    df = df[df["Prevailing Price (₱)"] <= 20000]

                    if not df.empty:
                        med = df["Prevailing Price (₱)"].median()
                        if med > 0:
                            df = df[df["Prevailing Price (₱)"] <= med * 5]
            return df
        except Exception as e:
            print(f"[ERROR] History Engine Error: {e}")
            st.cache_data.clear()
            return pd.DataFrame()

    @staticmethod
    @st.cache_data
    def load_reference_data():
        """Loads geospatial market coordinates safely."""
        REF_DATA_DIR = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "reference"
        )

        # 1. GEO DATA
        geo_path = os.path.join(REF_DATA_DIR, "markets_geo.csv")
        if os.path.exists(geo_path):
            geo_df = pd.read_csv(geo_path)
        else:
            geo_df = pd.DataFrame(columns=["market_name", "lat", "lon"])

        return geo_df

    @staticmethod
    def get_date_range():
        """
        Efficiently polls the clean layer to find the absolute MIN and MAX dates.
        """
        if not CLEAN_PATH:
            return None, None

        query = (
            "SELECT MIN(posting_date) as min_dt, MAX(posting_date) as max_dt "
            f"FROM {PRICES}"
        )

        try:
            con = DataEngine._get_connection()
            df = con.sql(query).df()
            con.close()

            if not df.empty and pd.notnull(df.iloc[0]["min_dt"]):
                # Use pd.to_datetime for robust parsing (handles timestamps)
                min_dt = pd.to_datetime(df.iloc[0]["min_dt"]).date()
                max_dt = pd.to_datetime(df.iloc[0]["max_dt"]).date()
                return min_dt, max_dt
            return None, None
        except Exception as e:
            print(f"[ERROR] Date Range Error: {e}")
            return None, None

    @staticmethod
    @st.cache_data(ttl=600)
    def get_available_dates():
        """
        Scans the clean layer partitions for available dates.
        Strictly ordered by date descending for UI selection.
        """
        if not CLEAN_PATH:
            return []

        query = (
            "SELECT DISTINCT posting_date as available_date "
            f"FROM {PRICES} ORDER BY 1 DESC"
        )

        try:
            con = DataEngine._get_connection()
            df = con.sql(query).df()
            con.close()
            return df["available_date"].astype(str).tolist()
        except Exception as e:
            print(f"[ERROR] Available Dates Error: {e}")
            return []

    @staticmethod
    def enrich_with_geo(df, geo_df):
        """
        Joins market data with geo data from the reference CSV.
        Prioritizes market-level precision over region-level approximations.
        """
        if df.empty:
            return df

        # Create a lookup for fast matching (deduplicate to prevent ValueError)
        geo_lookup = (
            geo_df.drop_duplicates(subset=["market_name"])
            .set_index("market_name")[["lat", "lon"]]
            .to_dict("index")
        )

        def get_coords(row):
            market = row.get("market_name")
            region = row.get("region_name")

            # 1. High Precision Market Lookup
            if market in geo_lookup:
                return geo_lookup[market]["lat"], geo_lookup[market]["lon"]

            # 2. Fallback to Region Center (with jitter)
            if region in REGION_CENTERS:
                base_lat, base_lon = REGION_CENTERS[region]
                lat_offset = random.uniform(-0.02, 0.02)
                lon_offset = random.uniform(-0.02, 0.02)
                return base_lat + lat_offset, base_lon + lon_offset

            return None, None

        coords = df.apply(get_coords, axis=1)
        df["lat"] = [c[0] for c in coords]
        df["lon"] = [c[1] for c in coords]

        return df.dropna(subset=["lat", "lon"])
