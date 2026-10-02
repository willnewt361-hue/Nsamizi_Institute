#!/usr/bin/env python3
# Backup script for Nsamizi system
import os  # For file operations
import datetime  # For timestamping backups
import shutil  # For copying files
import json  # For config

def backup_database():
    # Load config
    CFG_PATH = os.environ.get("NSAMIZI_CONFIG", "config.json")
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH,"r") as f:
            CFG = json.load(f)
    else:
        CFG = {"DB_URL": "sqlite:///nsamizi_demo.db"}
    
    db_url = CFG.get("DB_URL")
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups/{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    if db_url.startswith("sqlite:///"):
        # For SQLite, copy the db file
        db_file = db_url.replace("sqlite:///", "")
        if os.path.exists(db_file):
            shutil.copy(db_file, f"{backup_dir}/nsamizi_demo.db")
    elif db_url.startswith("postgresql://nsamizi_user"):
        # Dump PostgreSQL database
        import subprocess
        cmd = f"pg_dump '{db_url}' > {backup_dir}/database.sql"
        subprocess.run(cmd, shell=True)
    
    # Backup static files and templates
    if os.path.exists("static"):
        shutil.copytree("static", f"{backup_dir}/static")
    if os.path.exists("templates"):
        shutil.copytree("templates", f"{backup_dir}/templates")
    shutil.copy("app.py", f"{backup_dir}/app.py")
    shutil.copy("backup.py", f"{backup_dir}/backup.py")
    shutil.copy("recover.py", f"{backup_dir}/recover.py")
    
    print(f"Backup completed in {backup_dir}")

if __name__ == "__main__":
    backup_database()