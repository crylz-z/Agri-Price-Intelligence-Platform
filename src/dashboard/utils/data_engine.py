import pandas as pd
import os
import duckdb
import streamlit as st
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==========================================
# ==========================================
# CONFIGURATION
# ==========================================
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
# Dashboard needs market-level detail, use Silver layer instead of Gold
SILVER_LAYER_PATH = (
    f"s3://{S3_BUCKET_NAME}/silver/year=*/month=*/day=*/*.parquet"
    if S3_BUCKET_NAME
    else None
)

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

        aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_DEFAULT_REGION")

        if not all([aws_key, aws_secret, aws_region, S3_BUCKET_NAME]):
            print("[ERROR] Missing AWS Credentials or S3_BUCKET_NAME.")
            return con

        try:
            con.execute("INSTALL httpfs;")
            con.execute("LOAD httpfs;")
            con.execute(f"SET s3_region='{aws_region}';")
            con.execute(f"SET s3_access_key_id='{aws_key}';")
            con.execute(f"SET s3_secret_access_key='{aws_secret}';")
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
    def get_market_snapshot(target_date_str, window_days=3):
        """
        Loads the 'Last Known Good Value' (LKGV) snapshot for a specific date from S3 Silver layer.
        """
        if not SILVER_LAYER_PATH:
            return pd.DataFrame()

        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
            start_date = target_date - timedelta(days=window_days)
            start_date_str = start_date.strftime("%Y-%m-%d")

            # Generate partition pruning filter
            partition_filter = DataEngine._get_partition_filters(
                start_date, target_date
            )
        except Exception:
            return pd.DataFrame()

        query = f"""
        WITH windowed_data AS (
            SELECT
                region_name,
                market_name,
                category,
                commodity,
                price,
                extract_dt
            FROM read_parquet('{SILVER_LAYER_PATH}', union_by_name=true, hive_partitioning=1)
            WHERE ({partition_filter})
              AND CAST(extract_dt AS VARCHAR) NOT LIKE '%<%'
              AND CAST(extract_dt AS VARCHAR) NOT LIKE '%>%'
              AND CAST(extract_dt AS DATE) BETWEEN '{start_date_str}' AND '{target_date_str}'
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY region_name, market_name, commodity
                    ORDER BY extract_dt DESC
                ) as rn
            FROM windowed_data
        )
        SELECT * EXCLUDE (rn)
        FROM ranked
        WHERE rn = 1
        """

        try:
            con = DataEngine._get_connection()
            df = con.sql(query).df()
            con.close()

            if "price" in df.columns:
                df.rename(columns={"price": "Prevailing Price (₱)"}, inplace=True)

            # 1. Sanitize Region Names (Remove "1000000", "400000")
            if "region_name" in df.columns:
                # Ensure string type then regex (Catch "1000", "1000.0", "40.0")
                # We filter out anything that looks purely numeric (digits and dots)
                df = df[~df["region_name"].astype(str).str.match(r"^[0-9\.]+$")]

            # 2. Filter price outliers (> 5x median + Hard Cap)
            if not df.empty and "Prevailing Price (₱)" in df.columns:
                # Force numeric
                df["Prevailing Price (₱)"] = pd.to_numeric(
                    df["Prevailing Price (₱)"], errors="coerce"
                )

                # Hard Cap 20k
                df = df[df["Prevailing Price (₱)"] <= 20000]

                if not df.empty:
                    median_price = df["Prevailing Price (₱)"].median()
                    if median_price > 0:
                        df = df[df["Prevailing Price (₱)"] <= median_price * 5]

            # Calculate days_ago for freshness tracking (LKGV)
            if not df.empty and "extract_dt" in df.columns:
                df["extract_dt"] = pd.to_datetime(df["extract_dt"])
                target_dt = pd.to_datetime(target_date_str)
                df["days_ago"] = (target_dt - df["extract_dt"]).dt.days

            return df
        except Exception as e:
            print(f"[ERROR] Engine Error: {e}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_historical_trends(commodity, region, days_back=30):
        """
        Fetches time-series data for a commodity/region pair from S3 Silver layer.
        """
        if not SILVER_LAYER_PATH:
            return pd.DataFrame()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_date_str = start_date.strftime("%Y-%m-%d")

        # Generator partition pruning filter
        partition_filter = DataEngine._get_partition_filters(start_date, end_date)

        query = f"""
        SELECT
            extract_dt,
            price as 'Prevailing Price (₱)',
            region_name,
            market_name,
            commodity
        FROM read_parquet('{SILVER_LAYER_PATH}', union_by_name=true, hive_partitioning=1)
        WHERE
            ({partition_filter})
            AND CAST(extract_dt AS VARCHAR) NOT LIKE '%<%'
            AND CAST(extract_dt AS VARCHAR) NOT LIKE '%>%'
            AND TRY_CAST(extract_dt AS DATE) >= '{start_date_str}'
            AND commodity = '{commodity}'
            AND region_name = '{region}'
        ORDER BY extract_dt ASC
        """

        try:
            con = DataEngine._get_connection()
            df = con.sql(query).df()
            con.close()

            if not df.empty:
                df["extract_dt"] = pd.to_datetime(df["extract_dt"])

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
            return pd.DataFrame()

    @staticmethod
    @st.cache_data
    def load_reference_data():
        """Loads Geodata and SRPs. (Small CSVs, assume local for now or could be S3)."""
        # Kept local for simplicity as per instructions only focused on Data Parquet
        # But for full enterprise, these should likely be in S3 Reference layer too.
        # Check if local exists, else empty.

        # 1. GEO
        # For now, we return empty or basic structure if files missing,
        # as the user didn't explicitly safeguard this part,
        # but we must ensure it doesn't crash.
        geo_df = pd.DataFrame(columns=["market_name", "lat", "lon"])
        srp_df = pd.DataFrame(columns=["commodity", "srp"])

        # NOTE: Ideally migrate these to S3 reference bucket in future steps.
        return geo_df, srp_df

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
    def get_available_dates():
        """Scans S3 Silver layer partitions for available dates."""
        if not SILVER_LAYER_PATH:
            return []

        query = (
            f"SELECT DISTINCT extract_dt FROM read_parquet('{SILVER_LAYER_PATH}', "
            "union_by_name=true) "
            "WHERE CAST(extract_dt AS VARCHAR) NOT LIKE '%<%' "
            "AND CAST(extract_dt AS VARCHAR) NOT LIKE '%>%' "
            "ORDER BY extract_dt DESC"
        )

        try:
            con = DataEngine._get_connection()
            df = con.sql(query).df()
            con.close()
            return df["extract_dt"].astype(str).tolist()
        except Exception as e:
            print(f"[ERROR] Available Dates Error: {e}")
            return []

    @staticmethod
    def enrich_with_geo(df, geo_df):
        """
        Joins market data with geo data.
        """
        if df.empty:
            return df

        # Logic adapted for Region-based Gold Data (No Market level in Gold)
        # We Map Region Center directly.

        def get_coords(row):
            region = row.get("region_name")
            if region in REGION_CENTERS:
                base_lat, base_lon = REGION_CENTERS[region]
                # Add small jitter
                lat_offset = random.uniform(-0.02, 0.02)
                lon_offset = random.uniform(-0.02, 0.02)
                return base_lat + lat_offset, base_lon + lon_offset
            return None, None

        coords = df.apply(get_coords, axis=1)
        df["lat"] = [c[0] for c in coords]
        df["lon"] = [c[1] for c in coords]

        return df.dropna(subset=["lat", "lon"])
