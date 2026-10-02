#!/usr/bin/env python3
# Recovery script for Nsamizi system
import os  # For file operations
import shutil  # For copying files
import json  # For config

def recover_database(backup_dir):
    # Load config
    CFG_PATH = os.environ.get("NSAMIZI_CONFIG", "config.json")
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH,"r") as f:
            CFG = json.load(f)
    else:
        CFG = {"DB_URL": "sqlite:///nsamizi_demo.db"}
    
    db_url = CFG.get("DB_URL")
    
    if db_url.startswith("sqlite:///"):
        # For SQLite, copy the db file
        db_file = db_url.replace("sqlite:///", "")
        if os.path.exists(f"{backup_dir}/nsamizi_demo.db"):
            shutil.copy(f"{backup_dir}/nsamizi_demo.db", db_file)
    elif db_url.startswith("postgresql://"):
        # Restore PostgreSQL database
        import subprocess
        cmd = f"psql '{db_url}' < {backup_dir}/database.sql"
        subprocess.run(cmd, shell=True)
    
    # Restore files
    if os.path.exists(f"{backup_dir}/static"):
        shutil.copytree(f"{backup_dir}/static", "static", dirs_exist_ok=True)
    if os.path.exists(f"{backup_dir}/templates"):
        shutil.copytree(f"{backup_dir}/templates", "templates", dirs_exist_ok=True)
    shutil.copy(f"{backup_dir}/app-1.py", "app-1.py")
    shutil.copy(f"{backup_dir}/backup.py", "backup.py")
    shutil.copy(f"{backup_dir}/recover.py", "recover.py")
    
    print(f"Recovery completed from {backup_dir}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python recover.py <backup_dir>")
        sys.exit(1)
    recover_database(sys.argv[1])