"""Test DataEngine.get_date_range() to diagnose issue."""

from src.dashboard.utils.data_engine import DataEngine
from dotenv import load_dotenv

load_dotenv()

print("Testing DataEngine.get_date_range()...")
min_date, max_date = DataEngine.get_date_range()

print(f"min_date: {min_date}")
print(f"max_date: {max_date}")

if min_date and max_date:
    print(f"\n✅ Date range works: {min_date} to {max_date}")
else:
    print(f"\n❌ Date range failed")
