"""Read-only SQL over the lake, for checks and analysis.

    uv run python -m src.etl.query "SELECT \"table\", updated, count(*) FROM raw GROUP BY ALL"

Views: `raw`, every snapshot as PSA returned it (one column per month) plus `table`
and `updated` from the path; `mart`, the dbt mart `retail_prices_monthly`. A view the
query names may list its prefix (1 Class A op on R2), so run queries by hand, never
in a loop.
"""

import re
import sys
from collections.abc import Iterable

import duckdb
from dotenv import load_dotenv

from src.core import storage

READ_ONLY = ("SELECT", "WITH", "DESCRIBE", "SUMMARIZE", "FROM")
GLOBS = {
    "raw": "raw/table=*/updated=*.csv",
    "mart": "mart/retail_prices_monthly.parquet",
}
# PSA marks missing values "." or ".."; its CSV is Windows-1252, close enough to
# latin-1 for reading. updated=... is a file name, so hive partitioning skips it.
READERS = {
    "raw": "read_csv('{path}', hive_partitioning=true, union_by_name=true, "
    "filename=true, encoding='latin-1', nullstr=['.', '..'])",
    "mart": "read_parquet('{path}', filename=true)",
}
EXTRA = {
    "raw": ", regexp_extract(filename, 'updated=(\\w+)\\.csv', 1) AS updated",
    "mart": "",
}


def connect(root: str, names: Iterable[str] = GLOBS) -> duckdb.DuckDBPyConnection:
    """Views bind (and list their prefix) when created, so create only `names`."""
    con = duckdb.connect()
    con.execute("SET TimeZone = 'Asia/Manila'")
    if root.startswith("s3://"):
        storage.configure_duckdb(con)
    for name in names:
        reader = READERS[name].format(path=f"{root}/{GLOBS[name]}")
        con.execute(
            f"CREATE VIEW {name} AS SELECT * EXCLUDE (filename){EXTRA[name]} "
            f"FROM {reader}"
        )
    return con


def check_read_only(sql: str) -> None:
    words = sql.split(maxsplit=1)
    if not words or words[0].upper() not in READ_ONLY:
        raise ValueError(f"read-only: start the query with one of {READ_ONLY}")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    check_read_only(sys.argv[1])
    load_dotenv()
    sql = sys.argv[1]
    used = [n for n in GLOBS if re.search(rf"\b{n}\b", sql, re.IGNORECASE)]
    con = connect(storage.root(), used)  # keep a reference: .show() needs it open
    # .show() draws box characters a cp1252 Windows console can't encode.
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    con.sql(sql).show(max_rows=100)


if __name__ == "__main__":
    main()
