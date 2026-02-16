import pytest
from src.core.config import CATEGORY_MAP, REGION_MAP

def test_config_loaded():
    """Simple health check to ensure core config is importable and valid."""
    assert CATEGORY_MAP is not None
    assert len(CATEGORY_MAP) > 0
    assert REGION_MAP is not None
    assert len(REGION_MAP) > 0
    print("Health Check Passed: Config loaded successfully.")
