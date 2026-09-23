#!/usr/bin/env bash
# Automated Production PostgreSQL Backup Strategy
set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/var/backups/zecpath"
BACKUP_FILE="$BACKUP_DIR/zecpath_db_$TIMESTAMP.sql.gz"

mkdir -p $BACKUP_DIR

# Perform compressed streaming dump
pg_dump -U zecpath_user -h localhost zecpath_prod | gzip > $BACKUP_FILE

# Maintain only the last 7 days locally
find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +7 -exec rm {} +

echo "[$TIMESTAMP] Database backup completed: $BACKUP_FILE"
