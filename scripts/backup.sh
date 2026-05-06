#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/odoo_db_${TIMESTAMP}.sql.gz"

DB_CONTAINER="pizzeria-db-1"
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    DB_CONTAINER="pizzeria_db_1"
fi

if ! docker ps --format '{{.Names}}' | grep -q "$DB_CONTAINER"; then
    echo "ERROR: Database container not found. Is Docker running?"
    exit 1
fi

echo "[$(date)] Starting backup..."
docker exec "$DB_CONTAINER" pg_dump -U odoo postgres | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup saved: $BACKUP_FILE"
else
    echo "[$(date)] ERROR: Backup failed!"
    rm -f "$BACKUP_FILE"
    exit 1
fi

echo "[$(date)] Cleaning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "odoo_db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup complete. Current backups:"
ls -lh "$BACKUP_DIR"/odoo_db_*.sql.gz 2>/dev/null || echo "  (none)"