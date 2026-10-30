from unittest.mock import MagicMock, patch

import duckdb
from fsspec.implementations.local import LocalFileSystem

from src.dashboard.utils import data_engine
from src.dashboard.utils.data_engine import DataEngine
from src.etl import pipeline
from tests.test_pipeline import NOW, POSTED, make_records


@patch("duckdb.connect")
@patch("os.getenv", return_value="fake-bucket")
def test_connection_reads_s3_through_s3fs(_getenv, mock_connect):
    con = MagicMock()
    mock_connect.return_value = con
    assert DataEngine._get_connection() is con
    con.register_filesystem.assert_called_once()


def test_queries_read_clean_layer_in_page_shape(tmp_path, monkeypatch):
    root = tmp_path.as_posix()
    pipeline.run(LocalFileSystem(auto_mkdir=True), root, make_records(), NOW)
    path = f"{root}/clean/posting_date=*/prices.parquet"
    monkeypatch.setenv("S3_BUCKET_NAME", "local")
    monkeypatch.setattr(data_engine, "CLEAN_PATH", path)
    monkeypatch.setattr(
        data_engine,
        "PRICES",
        data_engine.PRICES.replace(data_engine.PRICES.split("'")[1], path),
    )
    monkeypatch.setattr(DataEngine, "_get_connection", staticmethod(duckdb.connect))

    assert DataEngine.get_available_dates() == [str(POSTED)]
    # A later target date falls back to the last posted date (LKGV).
    snap = DataEngine.get_market_snapshot("2026-10-30")
    assert {"region_name", "market_name", "category", "commodity", "extract_dt"} <= set(
        snap.columns
    )
    assert snap["days_ago"].unique().tolist() == [2]
    trend = DataEngine.get_historical_trends(
        "Rice - Regular", None, end_date_str="2026-10-30"
    )
    assert len(trend) == len(snap)
