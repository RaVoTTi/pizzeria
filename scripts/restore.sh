#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"

if [ $# -lt 1 ]; then
    echo "Usage: ./restore.sh <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -1t "$BACKUP_DIR"/odoo_db_*.sql.gz 2>/dev/null || echo "  (none found)"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: File not found: $BACKUP_FILE"
    exit 1
fi

DB_CONTAINER="pizzeria-db-1"
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    DB_CONTAINER="pizzeria_db_1"
fi

WEB_CONTAINER="pizzeria-web-1"
if ! docker ps --format '{{.Names}}' | grep -q "^${WEB_CONTAINER}$"; then
    WEB_CONTAINER="pizzeria_web_1"
fi

echo "============================================="
echo "  WARNING: This will REPLACE the current database!"
echo "============================================="
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Database container: $DB_CONTAINER"
echo ""
read -p "Are you sure you want to restore? (yes/NO): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "[1/4] Stopping Odoo..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" stop web

echo "[2/4] Restoring database..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U odoo postgres

echo "[3/4] Starting Odoo..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" start web

echo "[4/4] Waiting for Odoo to be ready..."
sleep 10

echo "Restore complete!"
echo "Access Odoo at: http://elgordo.local"