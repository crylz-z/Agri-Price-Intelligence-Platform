import pandas as pd
import os
import duckdb
import streamlit as st
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# S3 Path Config
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
SILVER_LAYER_PATH = (
    f"s3://{S3_BUCKET}/silver/year=*/month=*/day=*/*.parquet" if S3_BUCKET else None
)


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
    Uses DuckDB to query Parquet files directly from S3 Gold Layer.
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
            con.execute("INSTALL httpfs;")
            con.execute("LOAD httpfs;")
            con.execute(
                "CREATE SECRET IF NOT EXISTS (TYPE s3, PROVIDER credential_chain);"
            )
        except Exception as e:
            print(f"[ERROR] Failed to configure DuckDB S3: {e}")

        return con

    @staticmethod
    def _get_partition_filters(start_date, end_date):
        """
        Generates SQL WHERE clause for partition pruning based on date range.
        Assumes Hive-style partitioning: year=YYYY/month=MM/day=DD
        Returns: string like "(year = '2023' AND month = '10' AND day IN ('01', '02')) OR ..."
        """
        filters = []
        current = start_date
        while current <= end_date:
            y = str(current.year)
            m = f"{current.month:02d}"
            d = f"{current.day:02d}"
            filters.append(f"(year = '{y}' AND month = '{m}' AND day = '{d}')")
            current += timedelta(days=1)

        return " OR ".join(filters) if filters else "1=1"

    @staticmethod
    @st.cache_data(ttl=600)
    def get_market_snapshot(target_date_str, window_days=3, _cache_buster=2):
        """
        Loads the 'Last Known Good Value' (LKGV) snapshot for a specific date from S3 Silver layer.
        """
        bucket = os.getenv("S3_BUCKET_NAME")
        if not bucket:
            return pd.DataFrame()

        silver_path = f"s3://{bucket}/silver/year=*/month=*/day=*/*.parquet"

        try:
            datetime.strptime(target_date_str, "%Y-%m-%d")
            # 1. Retrieve absolute latest available date in S3 that is <= target_date
            # This ensures availability is not restricted by a fixed window during data gaps.
            con = DataEngine._get_connection()
            latest_available_query = f"""
                SELECT MAX(CAST(extract_dt AS DATE)) as latest_dt
                FROM read_parquet('{silver_path}', union_by_name=true, hive_partitioning=1)
                WHERE CAST(extract_dt AS DATE) <= '{target_date_str}'
                  AND CAST(extract_dt AS VARCHAR) NOT LIKE '%<%'
                  AND CAST(extract_dt AS VARCHAR) NOT LIKE '%>%'
            """
            latest_dt_df = con.sql(latest_available_query).df()

            if latest_dt_df.empty or pd.isnull(latest_dt_df.iloc[0]["latest_dt"]):
                con.close()
                return pd.DataFrame()

            lkgv_date = latest_dt_df.iloc[0]["latest_dt"]
            lkgv_date_str = lkgv_date.strftime("%Y-%m-%d")

            # 2. Load all records for the identified 'Last Known Good Date'
            query = f"""
            WITH daily_data AS (
                SELECT
                    region_name,
                    market_name,
                    category,
                    commodity,
                    price,
                    extract_dt
                FROM read_parquet('{silver_path}', union_by_name=true, hive_partitioning=1)
                WHERE CAST(extract_dt AS DATE) = '{lkgv_date_str}'
                  AND CAST(extract_dt AS VARCHAR) NOT LIKE '%<%'
                  AND CAST(extract_dt AS VARCHAR) NOT LIKE '%>%'
            ),
            ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY region_name, market_name, commodity
                        ORDER BY extract_dt DESC
                    ) as rn
                FROM daily_data
            )
            SELECT * EXCLUDE (rn)
            FROM ranked
            WHERE rn = 1
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
        Fetches time-series data for a commodity/region pair from S3 Silver layer.
        """
        bucket = os.getenv("S3_BUCKET_NAME")
        if not bucket:
            return pd.DataFrame()

        silver_path = f"s3://{bucket}/silver/year=*/month=*/day=*/*.parquet"

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except Exception:
                end_date = datetime.now()
        else:
            end_date = datetime.now()

        start_date = end_date - timedelta(days=days_back)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_formatted = end_date.strftime("%Y-%m-%d")

        # Generator partition pruning filter
        partition_filter = DataEngine._get_partition_filters(start_date, end_date)

        region_clause = f"AND region_name = '{region}'" if region else ""

        query = f"""
        SELECT
            extract_dt,
            price as 'Prevailing Price (₱)',
            region_name,
            market_name,
            commodity
        FROM read_parquet('{silver_path}', union_by_name=true, hive_partitioning=1)
        WHERE
            ({partition_filter})
            AND CAST(extract_dt AS VARCHAR) NOT LIKE '%<%'
            AND CAST(extract_dt AS VARCHAR) NOT LIKE '%>%'
            AND TRY_CAST(extract_dt AS DATE) >= '{start_date_str}'
            AND TRY_CAST(extract_dt AS DATE) <= '{end_date_formatted}'
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
        from src.core import config

        REF_DATA_DIR = os.path.join(
            config.BASE_DIR, "src", "dashboard", "assets", "reference"
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
        Efficiently polls the S3 Silver Parquet dataset to find the absolute MIN and MAX dates.
        """
        if not SILVER_LAYER_PATH:
            return None, None

        query = (
            "SELECT MIN(extract_dt) as min_dt, MAX(extract_dt) as max_dt "
            f"FROM read_parquet('{SILVER_LAYER_PATH}', union_by_name=true) "
            "WHERE CAST(extract_dt AS VARCHAR) NOT LIKE '%<%' "
            "AND CAST(extract_dt AS VARCHAR) NOT LIKE '%>%'"
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
        Scans S3 Silver layer partitions for available dates.
        Strictly ordered by date descending for UI selection.
        """
        if not SILVER_LAYER_PATH:
            return []

        query = (
            f"SELECT DISTINCT CAST(extract_dt AS DATE) as available_date "
            f"FROM read_parquet('{SILVER_LAYER_PATH}', union_by_name=true) "
            "WHERE CAST(extract_dt AS VARCHAR) NOT LIKE '%<%' "
            "AND CAST(extract_dt AS VARCHAR) NOT LIKE '%>%'"
            "ORDER BY 1 DESC"
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
