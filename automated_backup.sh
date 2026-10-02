#!/bin/bash
# Automated backup script for Nsamizi Institute
# Add to crontab: 0 2 * * * /path/to/backup.sh

BACKUP_DIR="/path/to/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

/path/to/your/venv/bin/python backup.py "$BACKUP_DIR"

# Keep only last 7 days of backups
find /path/to/backups -type d -mtime +7 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"
