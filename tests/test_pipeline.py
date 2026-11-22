import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fsspec.implementations.local import LocalFileSystem

from src.etl import pipeline


@pytest.fixture
def builds(monkeypatch):
    calls: list[None] = []
    monkeypatch.setattr(pipeline, "build", lambda: calls.append(None) or True)
    return calls


def test_no_new_snapshot_skips_dbt(builds):
    assert pipeline.run([])
    assert builds == []


def test_new_snapshot_runs_dbt(builds):
    assert pipeline.run(["s3://b/raw/table=X/updated=1.csv"])
    assert len(builds) == 1


def test_force_runs_dbt_without_new_snapshot(builds):
    assert pipeline.run([], force=True)
    assert len(builds) == 1


def test_dbt_failure_is_reported(monkeypatch):
    monkeypatch.setattr(pipeline, "build", lambda: False)
    assert not pipeline.run(["s3://b/raw/table=X/updated=1.csv"])


def test_stale_mart_runs_dbt(builds):
    assert pipeline.run([], is_stale=True)
    assert len(builds) == 1


@pytest.fixture
def lake(tmp_path):
    fs = LocalFileSystem(auto_mkdir=True)
    root = tmp_path.as_posix()
    for m in pipeline.MARTS:
        fs.pipe_file(f"{root}/mart/{m}.parquet", b"")
    return fs, root


def test_marts_built_after_the_newest_snapshot_are_fresh(lake):
    fs, root = lake
    snapshot = datetime(2000, 1, 1, tzinfo=UTC)
    assert not pipeline.stale(fs, root, snapshot)


def test_a_mart_older_than_the_newest_snapshot_is_stale(lake):
    fs, root = lake
    old = datetime(2000, 1, 1, tzinfo=UTC).timestamp()
    os.utime(f"{root}/mart/{pipeline.MARTS[0]}.parquet", (old, old))
    assert pipeline.stale(fs, root, datetime(2001, 1, 1, tzinfo=UTC))


def test_a_missing_mart_is_stale(lake):
    fs, root = lake
    fs.rm_file(f"{root}/mart/{pipeline.MARTS[-1]}.parquet")
    assert pipeline.stale(fs, root, datetime(2000, 1, 1, tzinfo=UTC))


def test_no_snapshot_is_never_stale(tmp_path):
    assert not pipeline.stale(LocalFileSystem(), tmp_path.as_posix(), None)


def test_marts_match_the_dbt_models():
    models = Path(pipeline.DBT_DIR, "models", "marts").glob("*.sql")
    assert sorted(p.stem for p in models) == list(pipeline.MARTS)
