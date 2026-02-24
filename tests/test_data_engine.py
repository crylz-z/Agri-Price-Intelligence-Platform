import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.dashboard.utils.data_engine import DataEngine


class TestDataEngine(unittest.TestCase):
    """
    Unit tests for the DataEngine class focusing on configuration
    and connection logic.
    """

    @patch("duckdb.connect")
    @patch("os.getenv")
    def test_connection_logic(self, mock_getenv, mock_duckdb):
        """Verify that DuckDB connection is initialized with external extensions."""
        mock_getenv.return_value = "fake-bucket"
        mock_con = MagicMock()
        mock_duckdb.return_value = mock_con

        con = DataEngine._get_connection()

        # Verify extensions are loaded
        mock_con.execute.assert_any_call("INSTALL httpfs;")
        mock_con.execute.assert_any_call("LOAD httpfs;")
        assert con == mock_con

    def test_partition_filter_generation(self):
        """Verify the Hive-partition filter string generation."""
        from datetime import datetime

        start = datetime(2026, 2, 1)
        end = datetime(2026, 2, 2)

        filters = DataEngine._get_partition_filters(start, end)

        assert "(year = '2026' AND month = '02' AND day = '01')" in filters
        assert "(year = '2026' AND month = '02' AND day = '02')" in filters
        assert "OR" in filters


if __name__ == "__main__":
    unittest.main()
