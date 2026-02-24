"""Pre-flight check: verify stack health (Alerting, Source, S3) before pipeline run."""

import os
import sys
import boto3
import requests
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError
from src.core.logger import get_logger
from src.core.config import BASE_URL

load_dotenv()

logger = get_logger(__name__)


def check_discord() -> None:
    """
    Validates that the Discord Webhook URL is present and appears valid.
    Logs a warning if missing or invalid, as this is non-fatal for data extraction.
    """
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        logger.warning("Discord Webhook URL not set. Alerting is DISABLED.")
        return

    if not url.startswith("https://discord.com/api/webhooks/"):
        logger.warning(
            "Discord Webhook URL seems invalid (does not start with expected prefix). Alerting may fail.",
            url_preview=url[:20] + "..." if url else None,
        )
    else:
        logger.info("Discord alerting configured.", url_preview=url[:35] + "...")


def check_source() -> None:
    """
    Validates connectivity to the DA Bantay Presyo source.
    Logs a warning if the source is unreachable, as the pipeline may still succeed
    via retries or valid cached data/partial extraction.
    """
    logger.info(f"Checking source connectivity: {BASE_URL} ...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Referer": "http://www.bantaypresyo.da.gov.ph/",
    }
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info("Data source is reachable.", status_code=response.status_code)
        elif response.status_code >= 500:
            logger.error(
                "Data source returned 500-level error. Failing fast.",
                status_code=response.status_code,
            )
            sys.exit(1)
        else:
            logger.warning(
                "Data source returned unexpected status code.",
                status_code=response.status_code,
            )
    except requests.exceptions.RequestException as e:
        logger.error("Data source is currently unreachable or degraded.", error=str(e))
        sys.exit(1)


def check_s3() -> None:
    """
    Validates S3 bucket access.
    This is a CRITICAL check. Failure here means we cannot read/write data.
    """
    bucket_name = os.getenv("S3_BUCKET_NAME")
    # If env var is empty string or None, fallback to default.
    configured_region = os.getenv("AWS_DEFAULT_REGION") or "ap-southeast-2"

    if not bucket_name:
        logger.error("S3_BUCKET_NAME not set.")
        sys.exit(1)

    logger.info(
        "Checking S3 bucket access...",
        bucket=bucket_name,
        region=configured_region,
    )

    try:
        # Create client in the CONFIGURED region
        s3 = boto3.client("s3", region_name=configured_region)
        s3.head_bucket(Bucket=bucket_name)
        logger.info("S3 bucket reachable.", bucket=bucket_name)

    except NoCredentialsError:
        logger.error("AWS credentials not found or invalid.")
        sys.exit(1)

    except ClientError as e:
        error_code = int(e.response["Error"]["Code"])

        if error_code == 404:
            logger.error("Bucket does not exist.", bucket=bucket_name)
            sys.exit(1)

        elif error_code in (301, 400):
            # 301/400 often means "Wrong Region". Let's find where it actually is.
            logger.warning(
                "Connection failed in configured region. Diagnosing actual region...",
                error_code=error_code,
                configured_region=configured_region,
            )
            try:
                # Use a client without a specific region to ask for location
                s3_global = boto3.client("s3")
                response = s3_global.get_bucket_location(Bucket=bucket_name)
                actual_region = response["LocationConstraint"] or "us-east-1"

                logger.error(
                    "Region Mismatch!",
                    expected=actual_region,
                    configured=configured_region,
                    action=f"Update AWS_DEFAULT_REGION in .env to '{actual_region}'.",
                )
                sys.exit(1)
            except Exception as diag_e:
                logger.error(
                    "Could not determine actual bucket region.", error=str(diag_e)
                )
                sys.exit(1)

        else:
            logger.error("S3 connection error.", error_code=error_code, error=str(e))
            sys.exit(1)


def main() -> None:
    """
    Execute stack validation suite.
    """
    check_discord()
    check_source()
    check_s3()
    logger.info("Pre-flight checks passed. Stack is healthy.")


if __name__ == "__main__":
    main()
