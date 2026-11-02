from datetime import timedelta

import pytest
from fsspec.implementations.local import LocalFileSystem

from src.etl import pipeline, query
from tests.test_pipeline import NOW, POSTED, make_records


def test_query_reads_raw_and_clean(tmp_path):
    fs, root = LocalFileSystem(auto_mkdir=True), tmp_path.as_posix()
    pipeline.run(fs, root, make_records(), NOW)
    pipeline.run(fs, root, make_records(), NOW + timedelta(hours=8))
    con = query.connect(root)

    raw = con.sql("SELECT count(*), count(DISTINCT run) FROM raw").fetchone()
    assert raw == (2 * len(make_records()), 2)
    clean = con.sql("SELECT count(*), max(posting_date) FROM clean").fetchone()
    assert clean == (len(make_records()), POSTED)


@pytest.mark.parametrize("sql", ["COPY raw TO 'x.csv'", "DROP VIEW raw", "  "])
def test_query_refuses_writes(sql):
    with pytest.raises(ValueError, match="read-only"):
        query.check_read_only(sql)
