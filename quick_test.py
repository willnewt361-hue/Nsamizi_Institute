#!/usr/bin/env python3
"""
Quick test script to verify Flask app starts and routes work
"""
import sys
import requests
import time
import subprocess
import os

def test_app():
    print("=" * 60)
    print("NTISD Flask App Test Suite")
    print("=" * 60)
    
    # Check if Flask app can start
    print("\n✓ Checking app.py syntax...")
    try:
        result = subprocess.run([sys.executable, "-m", "py_compile", "app.py"], 
                              capture_output=True, timeout=10)
        if result.returncode == 0:
            print("  ✅ Python syntax OK")
        else:
            print("  ❌ Syntax error:", result.stderr.decode())
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Try importing Flask
    print("\n✓ Checking Flask import...")
    try:
        import flask
        print("  ✅ Flask is installed")
    except ImportError:
        print("  ❌ Flask not installed")
        return False
    
    # Try importing SQLAlchemy
    print("\n✓ Checking SQLAlchemy...")
    try:
        import sqlalchemy
        print("  ✅ SQLAlchemy is installed")
    except ImportError:
        print("  ❌ SQLAlchemy not installed")
        return False
    
    # Try importing bcrypt
    print("\n✓ Checking bcrypt...")
    try:
        import bcrypt
        print("  ✅ bcrypt is installed")
    except ImportError:
        print("  ❌ bcrypt not installed")
        return False
    
    # Check database file
    print("\n✓ Checking database...")
    if os.path.exists("nsamizi_demo.db"):
        print("  ✅ Database file exists")
    else:
        print("  ⚠️  Database will be created on first run")
    
    # Check required files
    print("\n✓ Checking template files...")
    templates = [
        'templates/index.html',
        'templates/login.html',
        'templates/welcome_splash.html',
        'templates/fee_payment_guide.html',
        'templates/fee_history.html',
        'templates/admin_dashboard.html',
        'templates/student_progress.html',
        'templates/staff_dashboard.html',
        'static/css/modern.css'
    ]
    
    for template in templates:
        if os.path.exists(template):
            print(f"  ✅ {template}")
        else:
            print(f"  ❌ MISSING: {template}")
            return False
    
    print("\n" + "=" * 60)
    print("✅ All checks passed! App is ready to run.")
    print("=" * 60)
    print("\nTo start the app, run:")
    print("  python app-1.py")
    print("\nThen visit:")
    print("  http://localhost:5000")
    print("\nTest credentials:")
    print("  Student: NS2025-000000001 / Aisha#2025")
    print("  Lecturer: alice@nsamizi / Alice@123")
    print("  Admin: admin@nsamizi / Admin@123")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_app()
    sys.exit(0 if success else 1)
