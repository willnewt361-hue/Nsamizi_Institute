#!/usr/bin/env python3
"""
Nsamizi Institute - Production Setup Script
Automates additional production features and configurations.
Run this after basic setup to enable advanced features.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully.")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error in {description}: {e}")
        print(f"Output: {e.output}")
        return None

def setup_https():
    """Set up HTTPS using self-signed certificate for development."""
    print("🔒 Setting up HTTPS...")

    # Create certs directory
    certs_dir = Path("certs")
    certs_dir.mkdir(exist_ok=True)

    # Generate self-signed certificate
    key_file = certs_dir / "key.pem"
    cert_file = certs_dir / "cert.pem"

    if not key_file.exists() or not cert_file.exists():
        cmd = f'openssl req -x509 -newkey rsa:4096 -keyout "{key_file}" -out "{cert_file}" -days 365 -nodes -subj "/C=UG/ST=Central/O=Nsamizi Institute/CN=localhost"'
        run_command(cmd, "Generating self-signed SSL certificate")

    # Update app-1.py to use HTTPS
    app_file = Path("app-1.py")
    if app_file.exists():
        content = app_file.read_text()
        if "ssl_context" not in content:
            # Add SSL context to app.run()
            old_run = "if __name__ == '__main__':"
            new_run = """if __name__ == '__main__':
    # Enable HTTPS in production
    ssl_context = ('certs/cert.pem', 'certs/key.pem')
    app.run(host='0.0.0.0', port=5000, ssl_context=ssl_context, debug=False)"""
            content = content.replace(old_run, new_run)
            app_file.write_text(content)
            print("✅ Updated app-1.py for HTTPS")

    print("✅ HTTPS setup complete. Certificate files created in 'certs/' directory.")
    print("⚠️  Note: This uses a self-signed certificate. For production, use a proper CA certificate.")

def setup_gunicorn():
    """Set up Gunicorn for production deployment."""
    print("🚀 Setting up Gunicorn for production...")

    # Check if gunicorn is installed
    try:
        import gunicorn
    except ImportError:
        run_command("pip install gunicorn", "Installing Gunicorn")

    # Create gunicorn config
    config_content = """# Gunicorn configuration for Nsamizi Institute
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
user = "www-data"
group = "www-data"
tmp_upload_dir = None
"""

    config_file = Path("gunicorn.conf.py")
    config_file.write_text(config_content)
    print("✅ Created gunicorn.conf.py")

    # Create systemd service file
    service_content = """[Unit]
Description=Nsamizi Institute Web App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/app
Environment="PATH=/path/to/your/venv/bin"
ExecStart=/path/to/your/venv/bin/gunicorn --config gunicorn.conf.py app-1:app
Restart=always

[Install]
WantedBy=multi-user.target
"""

    service_file = Path("nsamizi.service")
    service_file.write_text(service_content)
    print("✅ Created nsamizi.service systemd file")
    print("📝 Edit the service file with correct paths before using.")

def setup_nginx():
    """Set up Nginx reverse proxy."""
    print("🌐 Setting up Nginx reverse proxy...")

    nginx_config = """# Nginx configuration for Nsamizi Institute
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /path/to/your/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

# HTTPS configuration (uncomment and configure SSL)
# server {
#     listen 443 ssl http2;
#     server_name your-domain.com;
#
#     ssl_certificate /path/to/cert.pem;
#     ssl_certificate_key /path/to/key.pem;
#
#     location / {
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#     }
#
#     location /static/ {
#         alias /path/to/your/app/static/;
#         expires 1y;
#         add_header Cache-Control "public, immutable";
#     }
# }
"""

    nginx_file = Path("nginx.conf")
    nginx_file.write_text(nginx_config)
    print("✅ Created nginx.conf")
    print("📝 Edit with your domain and paths before deploying.")

def setup_monitoring():
    """Set up basic monitoring and logging."""
    print("📊 Setting up monitoring...")

    # Create log directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Update app-1.py for better logging
    app_file = Path("app-1.py")
    if app_file.exists():
        content = app_file.read_text()
        if "logging" not in content:
            import_section = "import os"
            logging_setup = """
import logging
from logging.handlers import RotatingFileHandler

# Set up logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/nsamizi.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Nsamizi Institute startup')
"""
            content = content.replace(import_section, import_section + logging_setup)
            app_file.write_text(content)
            print("✅ Added logging to app-1.py")

def setup_backup_automation():
    """Set up automated backups."""
    print("💾 Setting up automated backups...")

    # Create backup script for cron
    cron_script = """#!/bin/bash
# Automated backup script for Nsamizi Institute
# Add to crontab: 0 2 * * * /path/to/backup.sh

BACKUP_DIR="/path/to/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

/path/to/your/venv/bin/python backup.py "$BACKUP_DIR"

# Keep only last 7 days of backups
find /path/to/backups -type d -mtime +7 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"
"""

    backup_script = Path("automated_backup.sh")
    backup_script.write_text(cron_script)
    backup_script.chmod(0o755)
    print("✅ Created automated_backup.sh")
    print("📝 Edit paths and add to crontab for daily backups.")

def main():
    """Main setup function."""
    print("🚀 Nsamizi Institute - Production Setup Script")
    print("=" * 50)

    features = {
        "1": ("HTTPS Setup", setup_https),
        "2": ("Gunicorn Setup", setup_gunicorn),
        "3": ("Nginx Setup", setup_nginx),
        "4": ("Monitoring & Logging", setup_monitoring),
        "5": ("Automated Backups", setup_backup_automation),
        "6": ("All Features", lambda: None)
    }

    print("Available features:")
    for key, (name, _) in features.items():
        print(f"  {key}. {name}")

    choice = input("\nSelect feature to set up (1-6): ").strip()

    if choice == "6":
        print("Setting up all features...")
        for _, func in list(features.values())[:-1]:  # Exclude "All Features"
            func()
    elif choice in features:
        features[choice][1]()
    else:
        print("❌ Invalid choice.")
        return

    print("\n✅ Setup complete!")
    print("📖 Check the generated files and edit paths as needed.")
    print("🔧 For production deployment, follow the instructions in the generated files.")

if __name__ == "__main__":
    main()