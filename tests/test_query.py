import pytest
from fsspec.implementations.local import LocalFileSystem

from src.etl import ingest, query
from tests.test_ingest import LISTING, FakeSession


def test_query_reads_raw_snapshots(tmp_path):
    fs, root = LocalFileSystem(auto_mkdir=True), tmp_path.as_posix()
    ingest.run(FakeSession(LISTING), fs, root, delay=0)
    con = query.connect(root, ["raw"])

    rows = con.sql(
        'SELECT "table", updated, count(*) FROM raw GROUP BY ALL ORDER BY 1'
    ).fetchall()
    assert rows == [
        ("0042M4ARN01", "20261002T081513", 3),
        ("0042M4ARN04", "20261002T081549", 3),
    ]
    # "." and ".." are missing values, not text.
    abra = con.sql(
        """SELECT "2018 January" FROM raw WHERE Geolocation = '....Abra' LIMIT 1"""
    ).fetchone()
    assert abra == (None,)
    national = con.sql(
        """SELECT "2018 January" FROM raw WHERE Geolocation = 'PHILIPPINES' LIMIT 1"""
    ).fetchone()
    assert national == (128.67,)


@pytest.mark.parametrize("sql", ["COPY raw TO 'x.csv'", "DROP VIEW raw", "  "])
def test_query_refuses_writes(sql):
    with pytest.raises(ValueError, match="read-only"):
        query.check_read_only(sql)
