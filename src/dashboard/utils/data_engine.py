import pandas as pd
import os
import glob
import streamlit as st
from datetime import datetime, timedelta
import random

# ==========================================
# CONFIGURATION
# ==========================================
CLEAN_DATA_DIR = "data/clean"
REF_DATA_DIR = "data/reference"

# REGION CENTERS (Approximate Lat/Lon)
# Used for fallback when specific market coordinates are missing
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
    "BARMM (Bangsamoro Autonomous Region of Muslim Mindanao)": (7.2245, 124.2687)
}

class DataEngine:
    """
    Centralized Data Access Layer for the Dashboard.
    Handles loading, caching, filtering, and enriching data.
    """

    @staticmethod
    @st.cache_data(ttl=600)
    def load_market_data(target_date_str, window_days=3):
        """
        Loads a window of data (Target + Previous Days).
        Implements the LKGV (Last Known Good Value) strategy via the window.
        """
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        except:
            return None
            
        frames = []
        for i in range(window_days):
            current_date = target_date - timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            filepath = os.path.join(CLEAN_DATA_DIR, f"market_prices_{date_str}.parquet")
            
            try:
                if os.path.exists(filepath):
                    df = pd.read_parquet(filepath)
                    # Helper: Ensure datetime column
                    if 'extract_dt' in df.columns:
                        df['extract_dt'] = pd.to_datetime(df['extract_dt'])
                    frames.append(df)
            except Exception:
                continue
                    
        if not frames:
            return pd.DataFrame()
            
        # COALESCE / SQUASH
        raw_df = pd.concat(frames, ignore_index=True)
        raw_df = raw_df.sort_values('extract_dt', ascending=False)
        
        # RENAME COLUMN (Ensuring consistency)
        if 'price' in raw_df.columns:
            raw_df.rename(columns={'price': 'Prevailing Price (₱)'}, inplace=True)
        elif 'PREVAILING RETAIL PRICE PER UNIT (P/UNIT)' in raw_df.columns:
            raw_df.rename(columns={'PREVAILING RETAIL PRICE PER UNIT (P/UNIT)': 'Prevailing Price (₱)'}, inplace=True)

        # DEDUP: Keep newest record per (Region, Market, Commodity)
        df = raw_df.drop_duplicates(subset=['region_name', 'market_name', 'commodity'], keep='first').copy()
        
        # CALCULATE FRESHNESS
        target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        df['days_ago'] = (target_dt - df['extract_dt']).dt.days
        df['days_ago'] = df['days_ago'].fillna(0).astype(int)
        
        return df

    @staticmethod
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def load_historical_data(commodity, region, days_back=30):
        """
        Loads time-series data for a specific commodity/region over a longer window.
        Does NOT squash dates. Preserves history for trend analysis.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        frames = []
        for i in range(days_back + 1):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            filepath = os.path.join(CLEAN_DATA_DIR, f"market_prices_{date_str}.parquet")
            
            try:
                if os.path.exists(filepath):
                    df = pd.read_parquet(filepath)
                    # Filter early to reduce memory
                    mask = (df['region_name'] == region) & (df['commodity'] == commodity)
                    filtered = df[mask].copy()
                    
                    if not filtered.empty:
                        # Ensure datetime
                        if 'extract_dt' in filtered.columns:
                            filtered['extract_dt'] = pd.to_datetime(filtered['extract_dt'])
                            
                        # Rename price col if needed
                        if 'price' in filtered.columns:
                            filtered.rename(columns={'price': 'Prevailing Price (₱)'}, inplace=True)
                        elif 'PREVAILING RETAIL PRICE PER UNIT (P/UNIT)' in filtered.columns:
                            filtered.rename(columns={'PREVAILING RETAIL PRICE PER UNIT (P/UNIT)': 'Prevailing Price (₱)'}, inplace=True)
                            
                        frames.append(filtered)
            except Exception:
                continue
                
        if not frames:
            return pd.DataFrame()
            
        # Combine
        full_df = pd.concat(frames, ignore_index=True)
        return full_df.sort_values('extract_dt')

    @staticmethod
    @st.cache_data
    def load_reference_data():
        """Loads Geodata and SRPs."""
        # 1. GEO
        geo_path = os.path.join(REF_DATA_DIR, "markets_geo.csv")
        if os.path.exists(geo_path):
            geo_df = pd.read_csv(geo_path)
            # Normalize market names in geo for better joining
            if 'market_name' in geo_df.columns:
                geo_df['market_name'] = geo_df['market_name'].astype(str).str.strip().str.title()
        else:
            geo_df = pd.DataFrame(columns=['market_name', 'lat', 'lon'])

        # 2. SRP
        srp_path = os.path.join(REF_DATA_DIR, "official_srp.csv")
        if os.path.exists(srp_path):
            srp_df = pd.read_csv(srp_path)
            if 'official_srp' in srp_df.columns:
                srp_df.rename(columns={'official_srp': 'srp'}, inplace=True)
        else:
            srp_df = pd.DataFrame(columns=['commodity', 'srp'])
        
        return geo_df, srp_df

    @staticmethod
    def get_available_dates():
        """Scans for available parquet files."""
        files = glob.glob(os.path.join(CLEAN_DATA_DIR, "market_prices_*.parquet"))
        dates = []
        for f in files:
            try:
                # expecting market_prices_YYYY-MM-DD.parquet
                basename = os.path.basename(f)
                date_str = basename.replace("market_prices_", "").replace(".parquet", "")
                dates.append(date_str)
            except:
                continue
        return sorted(dates, reverse=True)

    @staticmethod
    def enrich_with_geo(df, geo_df):
        """
        Joins market data with geo data.
        Implements RESILIENT JOIN: If exact market match fails, fall back to region center with jitter.
        """
        # 1. Strict Join
        merged = df.merge(geo_df, on='market_name', how='left')
        
        # 2. Fallback Logic
        def get_coords(row):
            # If we have valid coords from strict join, use them
            if pd.notnull(row['lat']) and pd.notnull(row['lon']):
                return row['lat'], row['lon']
            
            # Fallback: Region Center + Random Jitter
            region = row['region_name']
            if region in REGION_CENTERS:
                base_lat, base_lon = REGION_CENTERS[region]
                # Add small jitter so points don't stack perfectly (approx 1-2km radius)
                lat_offset = random.uniform(-0.02, 0.02)
                lon_offset = random.uniform(-0.02, 0.02)
                return base_lat + lat_offset, base_lon + lon_offset
            
            return None, None # Truly unknown location

        # Apply fallback
        coords = merged.apply(get_coords, axis=1)
        merged['lat'] = [c[0] for c in coords]
        merged['lon'] = [c[1] for c in coords]
        
        # Filter out rows that still have no coords (rare, only if unknown region)
        return merged.dropna(subset=['lat', 'lon'])
