import pytest

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
