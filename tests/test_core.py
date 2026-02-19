
import os
import sys
import requests
from unittest.mock import patch

# Adjust path to allow importing from scripts module at project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.logger import get_logger
from scripts.run_pipeline import send_discord_alert

def test_logger_initialization():
    """Verify that a logger instance is correctly initialized."""
    logger = get_logger("test")
    assert logger is not None

@patch("os.getenv")
def test_discord_alert_missing_webhook(mock_getenv):
    """
    Ensure the function exits gracefully (no-op) when
    DISCORD_WEBHOOK_URL is not set.
    """
    mock_getenv.return_value = None
    # Prior to this fix, this might have raised an error if logic wasn't robust.
    # We assert strictly that no exception is raised.
    try:
        send_discord_alert("Test message")
    except Exception as e:
        pytest.fail(f"send_discord_alert raised {e} unexpectedly when webhook is missing")

@patch("requests.post")
@patch("os.getenv")
def test_discord_alert_timeout(mock_getenv, mock_post):
    """
    Simulate a network timeout when sending a Discord alert.
    The function should catch the Timeout exception and log an error,
    preventing a pipeline crash.
    """
    mock_getenv.return_value = "https://discord.com/api/webhooks/fake"
    mock_post.side_effect = requests.exceptions.Timeout

    # Should not raise
    send_discord_alert("Test message")
