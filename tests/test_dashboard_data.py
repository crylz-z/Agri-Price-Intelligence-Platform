import duckdb
import pandas as pd

from src.dashboard import data

ROWS = """
    SELECT * REPLACE (price::DOUBLE AS price) FROM (VALUES
        (DATE '2026-08-01', '000000000', 'Philippines', 'national', 'Cereals', 'RICE', 55.0),
        (DATE '2026-09-01', '000000000', 'Philippines', 'national', 'Cereals', 'RICE', 55.68),
        (DATE '2026-09-01', '130000000', 'NCR - National Capital Region', 'region', 'Cereals', 'RICE', 60.0),
        (DATE '2026-09-01', '140000000', 'CAR - Cordillera Administrative Region', 'region', 'Cereals', 'RICE', 52.0),
        (DATE '2026-09-01', '140100000', 'Abra', 'province', 'Cereals', 'RICE', 50.0)
    ) AS t(month, geo_code, geolocation, geo_level, commodity_group, commodity, price)
"""


def make_lake(tmp_path) -> str:
    root = tmp_path.as_posix()
    (tmp_path / "mart").mkdir()
    duckdb.sql(f"COPY ({ROWS}) TO '{root}/{data.MART}' (FORMAT parquet)")
    return root


def test_read_mart_reads_the_parquet(tmp_path):
    df = data.read_mart(make_lake(tmp_path))
    assert len(df) == 5
    assert set(df["geo_level"]) == {"national", "region", "province"}


def test_geolocations_put_national_then_regions_then_provinces(tmp_path):
    df = data.read_mart(make_lake(tmp_path))
    assert data.geolocations(df) == [
        "Philippines",
        "CAR - Cordillera Administrative Region",
        "NCR - National Capital Region",
        "Abra",
    ]


def test_trend_is_one_series_per_geolocation_in_month_order(tmp_path):
    df = data.read_mart(make_lake(tmp_path))
    rows = data.trend(df, "RICE", ["Philippines"])
    assert list(rows["price"]) == [55.0, 55.68]


def test_compare_ranks_one_level_for_one_month(tmp_path):
    df = data.read_mart(make_lake(tmp_path))
    rows = data.compare(df, "RICE", pd.Timestamp("2026-09-01"), "region")
    assert list(rows["geolocation"]) == [
        "NCR - National Capital Region",
        "CAR - Cordillera Administrative Region",
    ]
