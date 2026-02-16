import os
import re
from pathlib import Path

DATA_DIR_RAW = Path("data/raw")

def standardize_filenames():
    print("Standardizing filenames in data/raw/...")
    
    # Walk all files
    for path in DATA_DIR_RAW.rglob("*.csv"):
        # We only care about prices_...csv
        if not path.name.startswith("prices_"):
            continue
            
        # Check if filename has date suffix: _YYYY_MM_DD.csv or _YYYY-MM-DD.csv
        # Pattern: prices_{region}_{date}.csv
        # We want: prices_{region}.csv
        
        filename = path.name
        stem = path.stem # prices_region_..._2026_02_16
        
        # Regex to find date suffix
        # Match _202\d[_-]\d{2}[_-]\d{2}$
        match = re.search(r'_202\d[_-]\d{2}[_-]\d{2}$', stem)
        
        if match:
            # It has a date suffix
            base_name = stem[:match.start()] # prices_region_...
            new_filename = f"{base_name}.csv"
            new_path = path.with_name(new_filename)
            
            if new_path.exists():
                print(f"  Conflict: {new_path} exists.")
                # If target exists, which one to keep?
                # If we assume target is newer (from recent run), keep target.
                # Delete source (dated file).
                print(f"  Removing redundant dated file: {path}")
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"  Failed remove {path}: {e}")
            else:
                print(f"  Renaming {path} -> {new_path}")
                try:
                    path.rename(new_path)
                except Exception as e:
                    print(f"  Failed rename {path}: {e}")
        else:
            # Already standardized or different format?
            # e.g. prices_region.csv -> Good.
            pass

    print("✅ Standardization Complete.")

if __name__ == "__main__":
    standardize_filenames()
