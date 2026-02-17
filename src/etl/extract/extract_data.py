import os
import time
import concurrent.futures
from datetime import datetime
import pandas as pd
import requests
from dotenv import load_dotenv

# Third-party libraries
import boto3
from botocore.exceptions import ClientError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Framework Imports
from src.core.config import REGION_MAP, CATEGORY_MAP, BASE_URL, RAW_DIR
from src.core.http_client import AgriHttpClient
from src.core.io_manager import IOManager
from src.utils.logger import get_logger

# Load Environment Variables
load_dotenv()

# Initialize Logger
logger = get_logger(__name__)

# Constants
URL_DATE = f"{BASE_URL}/tbl_price_get_date_rice.php"
URL_HEADER = f"{BASE_URL}/tbl_price_get_comm_header.php"
URL_PRICE = f"{BASE_URL}/tbl_price_get_comm_price.php"

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Initialize Core Components
http_client = AgriHttpClient()
io_manager = IOManager()


def to_snake_case(text):
    import re

    name = text.replace("(", "").replace(")", "")
    name = re.sub(r"[\s\-]+", "_", name)
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)
    return name.lower()


def send_discord_alert(region_name: str, error_msg: str):
    """Sends a lightweight alert to Discord on region failure."""
    if not DISCORD_WEBHOOK_URL:
        logger.warning(
            "Discord Webhook URL not set. Skipping alert.",
            region=region_name,
            error=error_msg,
        )
        return

    payload = {
        "content": (
            f"[CRITICAL FAILURE]: Extraction failed for region **{region_name}**.\n"
            f"Error: `{error_msg}`"
        )
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        logger.error("Failed to send Discord alert", error=str(e))


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(
        (requests.exceptions.RequestException, requests.exceptions.HTTPError)
    ),
)
def fetch_category_data(region_id, category_id, category_name):
    """
    Fetches data for a single category within a region with robust retries.
    Returns parsed rows or None on failure.
    """
    payload_base = {"region": region_id, "commodity": category_id}

    logger.debug(
        "Fetching category data",
        region_id=region_id,
        category=category_name,
        url=URL_DATE,
    )

    # Step 1: Get Date
    response = http_client.post(URL_DATE, data=payload_base)
    date_text = response.text

    # Step 2: Get Headers
    response = http_client.post(URL_HEADER, data=payload_base)
    headers_html = response.text

    # Parse Headers to get Markets
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(headers_html, "html.parser")
    markets = [
        td.get_text(strip=True) for td in soup.find_all("td", class_="text-wrap")
    ]
    markets = [m for m in markets if m and "SPECIFICATIONS" not in m.upper()]

    if not markets:
        return None

    # Step 3: Get Prices
    payload_price = payload_base.copy()
    payload_price["count"] = str(len(markets))

    response = http_client.post(URL_PRICE, data=payload_price)
    prices_html = response.text

    # Parse Prices
    parsed_data = parse_price_rows(
        prices_html, markets, region_id, category_name, date_text
    )
    return parsed_data


def parse_price_rows(html_rows, market_list, region_id, category_name, payload_date):
    """
    Parses the price HTML rows.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_rows, "html.parser")
    parsed_data = []
    rows = soup.find_all("tr")

    current_date_str = datetime.now().strftime("%Y-%m-%d")

    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        try:
            comm_name = cells[0].get_text(strip=True)
            specs = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            full_commodity_name = f"{comm_name} - {specs}" if specs else comm_name
            price_cells = cells[2:]

            for market, cell in zip(market_list, price_cells):
                price_str = cell.get_text(strip=True)
                if not price_str or price_str in ["N/A", "-", ""]:
                    continue

                try:
                    clean_price = float(price_str.replace(",", ""))
                except ValueError:
                    continue

                # Date resolution
                row_date = row.get("data-date") or row.get("data-price_date")
                final_date = current_date_str

                if row_date:
                    final_date = row_date
                elif payload_date:
                    try:
                        dt = datetime.strptime(payload_date, "%B %d, %Y")
                        final_date = dt.strftime("%Y-%m-%d")
                    except ValueError:
                        pass

                parsed_data.append(
                    {
                        "extract_dt": final_date,
                        "region_id": region_id,
                        "market_name": market,
                        "category": category_name,
                        "commodity": full_commodity_name,
                        "price": clean_price,
                    }
                )
        except Exception:
            continue

    return parsed_data


def process_region(args):
    """
    Worker function to process a single region.
    """
    region_id, region_name = args
    start_time = time.time()
    total_records = 0

    logger.info("START Region Processing", region=region_name, region_id=region_id)

    all_region_data = []

    try:
        for cat_id, cat_name in CATEGORY_MAP.items():
            try:
                # Fetch with retry
                rows = fetch_category_data(region_id, cat_id, cat_name)

                if rows:
                    all_region_data.extend(rows)

                time.sleep(0.5)  # Polite delay

            except Exception as e:
                # Individual category failure shouldn't kill the whole region instantly?
                # Or should we let it warn and continue?
                # User prompt said: "If a region fails completely after all retries..."
                # Fetch_category_data retries 5 times.
                # If it fails, it raises RetryError.
                # We catch it here.
                import traceback

                logger.warning(
                    "Category fetch failed",
                    region=region_name,
                    category=cat_name,
                    error=str(e),
                    traceback=traceback.format_exc(),
                )

        # Save Data (Immutability enforced)
        if all_region_data:
            df = pd.DataFrame(all_region_data)

            # Group by extract_dt
            for extract_dt, group in df.groupby("extract_dt"):
                # Deep Partitioning: data/raw/year={YYYY}/month={MM}/day={DD}/
                try:
                    dt_obj = datetime.strptime(extract_dt, "%Y-%m-%d")
                    year, month, day = (
                        dt_obj.strftime("%Y"),
                        dt_obj.strftime("%m"),
                        dt_obj.strftime("%d"),
                    )
                except ValueError:
                    # Fallback for unexpected format
                    # (should be YYYY-MM-DD from parse_price_rows)
                    year, month, day = extract_dt[:4], extract_dt[5:7], extract_dt[8:10]

                date_dir = os.path.join(
                    RAW_DIR, f"year={year}", f"month={month}", f"day={day}"
                )
                os.makedirs(date_dir, exist_ok=True)

                # Filename: prices_{region_snake}.csv (Idempotent)
                region_snake = to_snake_case(region_name)
                filename = f"prices_{region_snake}.csv"
                filepath = os.path.join(date_dir, filename)

                io_manager.save_dataframe(
                    group, filepath, file_format="csv", mode="overwrite"
                )
                total_records += len(group)

                logger.info("Data saved", filepath=filepath, rows=len(group))

                # Cloud Ingestion (Bronze Layer) - Fallback Pattern
                try:
                    s3_bucket = os.getenv("S3_BUCKET_NAME")
                    if s3_bucket:
                        # Key structure:
                        # bronze/year={YYYY}/month={MM}/day={DD}/filename.csv
                        s3_key = (
                            f"bronze/year={year}/month={month}/day={day}/{filename}"
                        )

                        s3_client = boto3.client("s3")
                        s3_client.upload_file(filepath, s3_bucket, s3_key)

                        logger.info(
                            "[CLOUD] Uploaded to S3 (Bronze)",
                            bucket=s3_bucket,
                            key=s3_key,
                        )
                    else:
                        logger.warning("S3_BUCKET_NAME not set. Skipping cloud upload.")

                except ClientError as e:
                    # FALLBACK: We already saved locally. Log structured JSON error.
                    error_msg = f"S3 Upload ClientError: {e.response.get('Error', {})}"
                    logger.error(
                        "[WARN] S3 Upload Failed (ClientError)",
                        region=region_name,
                        error=e.response.get("Error", {}),
                        file=filepath,
                    )
                    send_discord_alert(region_name, error_msg)
                except Exception as e:
                    error_msg = f"S3 Upload Generic Failure: {str(e)}"
                    logger.error(
                        "[WARN] S3 Upload Generic Failure",
                        region=region_name,
                        error=str(e),
                    )
                    send_discord_alert(region_name, error_msg)

        duration = time.time() - start_time
        logger.info(
            "[INFO] DONE Region",
            region=region_name,
            rows=total_records,
            duration=f"{duration:.2f}s",
        )
        return (region_name, "OK", total_records, duration)

    except Exception as e:
        # Circuit Breaker & Alerting
        duration = time.time() - start_time
        error_msg = str(e)
        logger.error("[ERROR] FAIL Region", region=region_name, error=error_msg)

        # DLQ Logic (Deep Partitioning)
        try:
            current_date = datetime.now()
            year, month, day = (
                current_date.strftime("%Y"),
                current_date.strftime("%m"),
                current_date.strftime("%d"),
            )

            dlq_dir = os.path.join(
                "data", "dlq", f"year={year}", f"month={month}", f"day={day}"
            )
            os.makedirs(dlq_dir, exist_ok=True)

            region_snake = to_snake_case(region_name)
            filename = f"failed_prices_{region_snake}.csv"  # Idempotent filename
            filepath = os.path.join(dlq_dir, filename)

            # Save error record
            error_df = pd.DataFrame(
                [
                    {
                        "region_name": region_name,
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat(),
                    }
                ]
            )
            io_manager.save_dataframe(
                error_df, filepath, file_format="csv", mode="overwrite"
            )
            logger.info("Saved to DLQ", filepath=filepath)

        except Exception as dlq_error:
            logger.error("Failed to save to DLQ", error=str(dlq_error))

        send_discord_alert(region_name, error_msg)
        return (region_name, f"FAIL ({error_msg})", 0, duration)


def main():
    logger.info("Starting Extraction Engine V3.2 (Fail-Fast Timeout Constraints)...")
    logger.info("Configuration", regions=len(REGION_MAP), workers=5, timeout="900s")

    pipeline_start = time.time()
    results = []
    REGION_TIMEOUT = 900  # 15 minutes per region

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        region_args = [(rid, rname) for rid, rname in REGION_MAP.items()]
        
        # Submit all futures
        future_to_region = {
            executor.submit(process_region, args): args[1] for args in region_args
        }

        # Process completed futures with timeout
        for future in concurrent.futures.as_completed(future_to_region, timeout=None):
            region_name = future_to_region[future]
            try:
                res = future.result(timeout=REGION_TIMEOUT)
                results.append(res)
            except concurrent.futures.TimeoutError:
                # Region exceeded 15-minute timeout
                error_msg = f"Region timeout: exceeded {REGION_TIMEOUT}s limit"
                logger.error(
                    "[TIMEOUT] Region abandoned",
                    region=region_name,
                    timeout=f"{REGION_TIMEOUT}s",
                )
                send_discord_alert(region_name, error_msg)
                results.append((region_name, "TIMEOUT", 0, REGION_TIMEOUT))
            except Exception as e:
                # Catch any other execution exceptions
                error_msg = f"Region execution error: {str(e)}"
                logger.error("[ERROR] Region execution failed", region=region_name, error=str(e))
                send_discord_alert(region_name, error_msg)
                results.append((region_name, f"ERROR ({str(e)})", 0, 0))

    pipeline_end = time.time()
    total_duration = pipeline_end - pipeline_start
    total_rows = sum(r[2] for r in results)

    # PERFORMANCE REPORT
    logger.info(
        "PERFORMANCE REPORT",
        total_duration=f"{total_duration:.2f}s",
        total_rows=total_rows,
    )

    for rname, status, rows, dur in results:
        dur_str = f"{dur:.2f}s"
        logger.info(
            "Region Stats", region=rname, status=status, rows=rows, duration=dur_str
        )

    logger.info("Extraction Complete", total_rows=total_rows)

    # Human-Readable Summary
    print("\n" + "=" * 80)
    print(f"{'REGION':<40} | {'STATUS':<10} | {'ROWS':<8} | {'TIME'}")
    print("-" * 80)

    success_count = 0
    failure_count = 0

    for rname, status, rows, dur in results:
        if status == "OK":
            success_count += 1
        else:
            failure_count += 1

        print(f"{rname:<40} | {status:<10} | {rows:<8} | {dur:.2f}s")

    print("-" * 80)
    print(f"Total Time:      {total_duration:.2f}s")
    print(f"Total Rows:      {total_rows}")
    print(f"Successful:      {success_count}")
    print(f"Failed:          {failure_count}")
    print("=" * 80 + "\n")

    # Trigger Downstream (Silver Layer)
    logger.info("Etl Pipeline Decoupled. Transformation must be triggered separately.")


if __name__ == "__main__":
    main()
