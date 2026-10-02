#!/usr/bin/env python3
"""
PostgreSQL Setup & Migration Script for Nsamizi Digital Fortress
- Creates database and user
- Tests connection
- Verifies schema
- Ready for production

Run: python setup_postgresql.py
"""

import subprocess
import sys
import os
import json
from pathlib import Path

# Configuration
DB_NAME = "nsamizi_db"
DB_USER = "nsamizi_user"
DB_PASSWORD = "##000000"
DB_HOST = "localhost"
DB_PORT = 5432

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

def print_header(text):
    """Print section header"""
    print(f"\n{BLUE}{'='*70}{END}")
    print(f"{BLUE}{text.center(70)}{END}")
    print(f"{BLUE}{'='*70}{END}\n")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓ {text}{END}")

def print_error(text):
    """Print error message"""
    print(f"{RED}✗ {text}{END}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠ {text}{END}")

def print_info(text):
    """Print info message"""
    print(f"{BLUE}ℹ {text}{END}")

def run_psql_command(command, as_user=None):
    """Run psql command"""
    try:
        if as_user:
            cmd = f'psql -U {as_user} -c "{command}"'
        else:
            cmd = f'psql -U postgres -c "{command}"'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def check_postgresql():
    """Check if PostgreSQL is installed and running"""
    print_header("Checking PostgreSQL Installation")
    
    success, output = run_psql_command("SELECT version();")
    
    if success:
        print_success("PostgreSQL is installed and running")
        print(f"  {output.split(',')[0]}")
        return True
    else:
        print_error("PostgreSQL is not running or not found")
        print_warning("Please ensure PostgreSQL 18.3 is installed and running")
        return False

def create_database():
    """Create PostgreSQL database"""
    print_header(f"Creating Database: {DB_NAME}")
    
    success, output = run_psql_command(f"CREATE DATABASE {DB_NAME};")
    
    if success:
        print_success(f"Database '{DB_NAME}' created successfully")
        return True
    else:
        if "already exists" in output:
            print_warning(f"Database '{DB_NAME}' already exists")
            return True
        else:
            print_error(f"Failed to create database: {output}")
            return False

def create_user():
    """Create PostgreSQL user"""
    print_header(f"Creating Database User: {DB_USER}")
    
    success, output = run_psql_command(
        f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}';"
    )
    
    if success:
        print_success(f"User '{DB_USER}' created successfully")
        return True
    else:
        if "already exists" in output:
            print_warning(f"User '{DB_USER}' already exists")
            return True
        else:
            print_error(f"Failed to create user: {output}")
            return False

def grant_privileges():
    """Grant privileges to user"""
    print_header(f"Granting Privileges to {DB_USER}")
    
    commands = [
        f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};",
        f"GRANT CREATE ON SCHEMA public TO {DB_USER};",
    ]
    
    for cmd in commands:
        success, output = run_psql_command(cmd)
        if success:
            print_success(f"Granted: {cmd.split('GRANT')[1][:50]}...")
        else:
            print_warning(f"Could not grant privilege: {output}")
    
    return True

def test_connection():
    """Test database connection"""
    print_header("Testing Database Connection")
    
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    print_info(f"Connection String: postgresql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    try:
        from sqlalchemy import create_engine, text
        
        engine = create_engine(connection_string, echo=False, future=True)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print_success("Database connection successful!")
            return True, connection_string
    except Exception as e:
        print_error(f"Connection failed: {str(e)}")
        return False, connection_string

def verify_schema():
    """Verify database schema exists"""
    print_header("Verifying Database Schema")
    
    try:
        from sqlalchemy import create_engine, inspect
        
        connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(connection_string, echo=False, future=True)
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if len(tables) > 0:
            print_success(f"Found {len(tables)} tables in database:")
            for table in sorted(tables):
                print(f"  • {table}")
            return True
        else:
            print_warning("No tables found. You'll need to run Flask app to create schema.")
            return True
    except Exception as e:
        print_error(f"Could not verify schema: {str(e)}")
        return False

def update_config():
    """Update config.json with PostgreSQL URL"""
    print_header("Updating Configuration")
    
    config_path = "config.json"
    
    if not os.path.exists(config_path):
        print_warning(f"config.json not found at {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update DB_URL
        config["DB_URL"] = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print_success("config.json updated with PostgreSQL connection string")
        print_info(f"Database: {DB_NAME}")
        print_info(f"User: {DB_USER}")
        print_info(f"Host: {DB_HOST}:{DB_PORT}")
        return True
    except Exception as e:
        print_error(f"Failed to update config: {str(e)}")
        return False

def create_env_file():
    """Create .env file for environment variables"""
    print_header("Creating .env File (Optional but Recommended)")
    
    env_content = f"""# Nsamizi Digital Fortress - Environment Variables
DATABASE_URL=postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}
SECRET_KEY=nsamizi-secret-key-2026-production
FLASK_ENV=production
FLASK_DEBUG=False
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print_success(".env file created")
        print_warning("IMPORTANT: Add .env to .gitignore to keep secrets safe!")
        return True
    except Exception as e:
        print_error(f"Failed to create .env: {str(e)}")
        return False

def main():
    """Main setup function"""
    print(f"\n{BLUE}")
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  Nsamizi Digital Fortress - PostgreSQL Setup Script          ║
    ║  Version 1.0 | May 2026                                      ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    print(END)
    
    # Step 1: Check PostgreSQL
    if not check_postgresql():
        print_error("PostgreSQL setup failed!")
        sys.exit(1)
    
    # Step 2: Create database
    if not create_database():
        print_warning("Continuing with existing database...")
    
    # Step 3: Create user
    if not create_user():
        print_warning("Continuing with existing user...")
    
    # Step 4: Grant privileges
    grant_privileges()
    
    # Step 5: Test connection
    connection_ok, conn_str = test_connection()
    if not connection_ok:
        print_error("PostgreSQL setup encountered issues!")
        sys.exit(1)
    
    # Step 6: Verify schema
    verify_schema()
    
    # Step 7: Update config
    update_config()
    
    # Step 8: Create .env file
    create_env_file()
    
    # Final summary
    print_header("Setup Complete!")
    print_success("PostgreSQL database is ready!")
    print(f"\n{YELLOW}Next Steps:{END}")
    print(f"1. Run Flask app: {BLUE}python app-1.py{END}")
    print(f"2. Tables will be created automatically")
    print(f"3. Demo data will be seeded")
    print(f"4. Navigate to http://127.0.0.1:5000")
    print(f"\n{YELLOW}Database Credentials:{END}")
    print(f"  Host:     {DB_HOST}")
    print(f"  Port:     {DB_PORT}")
    print(f"  Database: {DB_NAME}")
    print(f"  User:     {DB_USER}")
    print(f"  Password: {'*' * len(DB_PASSWORD)}")
    print()

if __name__ == "__main__":
    main()
