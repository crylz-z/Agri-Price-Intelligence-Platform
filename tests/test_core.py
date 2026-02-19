import pytest

def test_basic_math():
    """A trivial test to ensure pytest is working."""
    assert 1 + 1 == 2

def test_python_version():
    """Ensure the environment is running the correct Python version."""
    import sys
    assert sys.version_info >= (3, 11)
