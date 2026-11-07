import pytest

from src.core import storage


def test_endpoint_url_rejects_bucket_path(monkeypatch):
    base = "https://acct.r2.cloudflarestorage.com"
    monkeypatch.setenv("S3_ENDPOINT_URL", base + "/")
    assert storage.endpoint_url() == base + "/"
    monkeypatch.setenv("S3_ENDPOINT_URL", base + "/apip-data-lake")
    with pytest.raises(ValueError, match="drop the bucket"):
        storage.endpoint_url()
