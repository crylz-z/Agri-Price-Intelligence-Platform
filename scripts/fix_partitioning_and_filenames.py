import os
import shutil
import re
import glob
from pathlib import Path

DATA_DIR_RAW = Path("data/raw")
DATA_DIR_DLQ = Path("data/dlq")

def to_snake_case(text):
    # Same logic as extract_data.py for consistency
    name = text.replace("(", "").replace(")", "")
    name = re.sub(r'[\s\-]+', '_', name)
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    return name.lower()

def cleanup_raw_timestamps():
    print("🧹 Cleaning up timestamped files in data/raw...")
    # Matches files like prices_region_name_1771228999.csv
    # But wait, snake_case conversion might have already happened or not?
    # User said "Delete any CSVs containing a 10-digit UNIX timestamp in the data/raw/year=2026/... directories."
    
    # We iterate recursively
    for path in DATA_DIR_RAW.rglob("*.csv"):
        filename = path.name
        # Check for 10 consecutive digits (timestamp)
        match = re.search(r'_(\d{10})\.csv$', filename)
        if match:
            print(f"  Deleting timestamped file: {path}")
            try:
                os.remove(path)
            except Exception as e:
                print(f"  Failed delete {path}: {e}")

def migrate_ghost_folder():
    print("👻 Migrating ghost folder data/raw/2026-02-16...")
    ghost_path = DATA_DIR_RAW / "2026-02-16"
    if not ghost_path.exists():
        print("  Ghost folder not found.")
        return

    # Target: data/raw/year=2026/month=02/day=16/
    target_dir = DATA_DIR_RAW / "year=2026" / "month=02" / "day=16"
    os.makedirs(target_dir, exist_ok=True)
    
    for file_path in ghost_path.glob("*.csv"):
        filename = file_path.name
        # If filename has timestamp, remove it. If not, just ensure snake_case.
        # Logic: strip timestamp if present, snake_case rest.
        
        # Strip timestamp suffix if present
        name_no_ext = file_path.stem
        match = re.search(r'_\d{10}$', name_no_ext)
        if match:
            base_name = name_no_ext[:match.start()]
        else:
            base_name = name_no_ext
            
        new_name_snake = to_snake_case(base_name)
        new_filename = f"prices_{new_name_snake}.csv"
        
        # If input filename didn't start with prices_ (legacy might differ), adjust
        if not new_filename.startswith("prices_"):
            # Check if base_name already had prices?
            if "prices_" in base_name:
                # it's fine
                pass
            else:
                 new_filename = f"prices_{new_name_snake}.csv"

        # The migration script output showed: prices_region_iii_central_luzon.csv
        # If we double prefix, e.g. prices_prices_..., that's bad.
        # to_snake_case just formats.
        # Let's simple check: if starts with prices_, keep it. 
        if not new_filename.startswith("prices_"):
             new_filename = "prices_" + new_filename.replace("prices_", "")

        new_path = target_dir / new_filename
        
        print(f"  Moving {file_path} -> {new_path}")
        shutil.move(str(file_path), str(new_path))

    # Delete ghost folder
    try:
        shutil.rmtree(ghost_path)
        print("  Deleted ghost folder.")
    except Exception as e:
        print(f"  Failed delete ghost folder: {e}")

def migrate_dlq():
    print("🚧 Migrating DLQ...")
    # Iterates data/dlq/YYYY-MM-DD
    # Moves to data/dlq/year=YYYY/month=MM/day=DD
    # Filename: failed_prices_{region_snake}.csv (remove timestamp)
    
    for date_dir in DATA_DIR_DLQ.glob("202*-*-*"):
        if not date_dir.is_dir(): continue
        
        date_str = date_dir.name
        try:
            year, month, day = date_str.split('-')
        except ValueError:
            continue
            
        target_dir = DATA_DIR_DLQ / f"year={year}" / f"month={month}" / f"day={day}"
        os.makedirs(target_dir, exist_ok=True)
        
        for file_path in date_dir.glob("*.csv"):
             # failed_prices_NCR (NATIONAL CAPITAL REGION)_2026-02-09.csv
             # We want: failed_prices_ncr_national_capital_region.csv
             
             stem = file_path.stem # failed_prices_NCR (NATIONAL CAPITAL REGION)_2026-02-09
             
             # Remove date/timestamp suffix?
             # The example shows date suffix: _2026-02-09
             # Start by removing known date-like suffix
             stem_clean = re.sub(r'_\d{4}-\d{2}-\d{2}$', '', stem)
             # regex for unixtimestamp?
             stem_clean = re.sub(r'_\d{10}$', '', stem_clean)
             
             # snake_case
             snake_name = to_snake_case(stem_clean)
             
             # Ensure prefix
             if not snake_name.startswith("failed_prices_"):
                 if "failed_prices" in snake_name:
                      pass
                 else:
                      snake_name = "failed_prices_" + snake_name

             new_filename = f"{snake_name}.csv"
             new_path = target_dir / new_filename
             
             print(f"  Moving {file_path} -> {new_path}")
             shutil.move(str(file_path), str(new_path))
             
        # Delete old dir
        try:
            shutil.rmtree(date_dir)
            print(f"  Deleted legacy DLQ: {date_dir}")
        except Exception as e:
            print(f"  Failed delete DLQ dir {date_dir}: {e}")

def main():
    cleanup_raw_timestamps()
    migrate_ghost_folder()
    migrate_dlq()
    print("✅ Partitioning & Filename Fixes Complete.")

if __name__ == "__main__":
    main()
