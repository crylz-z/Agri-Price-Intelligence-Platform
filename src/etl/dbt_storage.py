"""dbt-duckdb plugin: give dbt's DuckDB connection the lake's s3fs filesystem."""

from dbt.adapters.duckdb.plugins import BasePlugin
from duckdb import DuckDBPyConnection

from src.core import storage


class Plugin(BasePlugin):
    def configure_connection(self, conn: DuckDBPyConnection) -> None:
        storage.configure_duckdb(conn)
