import os
import shutil
import glob

def cleanup():
    print("🧹 Starting Legacy Cleanup...")
    
    # 1. Clean data/raw/YYYY-MM-DD
    raw_legacy = glob.glob("data/raw/202*-*-*")
    for path in raw_legacy:
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
                print(f"  Deleted: {path}")
            except Exception as e:
                print(f"  Failed to delete {path}: {e}")

    # 2. Clean data/clean/date=*
    clean_legacy = glob.glob("data/clean/date=*")
    for path in clean_legacy:
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
                print(f"  Deleted: {path}")
            except Exception as e:
                print(f"  Failed to delete {path}: {e}")

    # 3. Clean data/gold/date=*
    gold_legacy = glob.glob("data/gold/date=*")
    for path in gold_legacy:
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
                print(f"  Deleted: {path}")
            except Exception as e:
                print(f"  Failed to delete {path}: {e}")

    print("✅ Cleanup Complete.")

if __name__ == "__main__":
    cleanup()
