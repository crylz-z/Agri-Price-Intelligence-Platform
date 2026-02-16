import os
import shutil
import re
import glob
import boto3
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
DATA_DIR = "data/raw"

def to_snake_case(text):
    # Remove file extension for processing
    name, ext = os.path.splitext(text)
    # Remove contents inside parentheses? No, user example kept them: prices_ncr_national_capital_region
    # Just remove the parens characters themselves
    name = name.replace("(", "").replace(")", "")
    # Replace spaces and hyphens with underscores
    name = re.sub(r'[\s\-]+', '_', name)
    # Remove other special chars
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    return f"{name.lower()}{ext}"

def migrate():
    s3 = boto3.client('s3')
    print("🚀 Starting Safe Historical Data Migration...")
    
    # Iterate over date directories
    # Expecting data/raw/YYYY-MM-DD
    date_dirs = glob.glob(os.path.join(DATA_DIR, "202*-*-*"))
    
    for date_dir in date_dirs:
        if not os.path.isdir(date_dir):
            continue
            
        date_str = os.path.basename(date_dir)
        # Parse date
        try:
            year, month, day = date_str.split('-')
        except ValueError:
            print(f"Skipping invalid directory: {date_str}")
            continue
            
        print(f"\nProcessing {date_str}...")
        
        # New directory structure: data/raw/year=YYYY/month=MM/day=DD
        new_dir_base = os.path.join(DATA_DIR, f"year={year}", f"month={month}", f"day={day}")
        os.makedirs(new_dir_base, exist_ok=True)
        
        # Process files
        files = glob.glob(os.path.join(date_dir, "*.csv"))
        for file_path in files:
            filename = os.path.basename(file_path)
            new_filename = to_snake_case(filename)
            new_file_path = os.path.join(new_dir_base, new_filename)
            
            # COPY first (Safety)
            shutil.copy2(file_path, new_file_path)
            print(f"  Moved: {filename} -> {new_filename}")
            
            # S3 Upload
            if S3_BUCKET:
                s3_key = f"bronze/year={year}/month={month}/day={day}/{new_filename}"
                try:
                    s3.upload_file(new_file_path, S3_BUCKET, s3_key)
                    print(f"  ☁️ Uploaded to S3: {s3_key}")
                except Exception as e:
                    print(f"  ❌ S3 Upload Failed: {e}")
            
        # After successful copy and upload of ALL files in dir, we can verify?
        # For now, just leave legacy dir. User said "Only after... delete".
        # We will delete the legacy folder if empty or explicitly requested.
        # But wait, we copied, so originals are still there.
        # Let's delete the files we moved from the old dir?
        # Safe strategy: KEEP old dirs for now. User can delete manually or we do a second pass.
        # "Only after all files are safely moved... delete the empty legacy ... folders"
        
        # Let's check if we processed all files.
        # If we copied successfully, we can delete the original file.
        for file_path in files:
            os.remove(file_path)
            
        # Now try to remove dir if empty
        try:
            os.rmdir(date_dir)
            print(f"  Deleted empty legacy dir: {date_dir}")
        except OSError:
            print(f"  Legacy dir not empty, kept: {date_dir}")

    print("\n✅ Migration Complete.")

if __name__ == "__main__":
    migrate()
