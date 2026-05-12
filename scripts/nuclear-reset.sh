#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Soft reset path: clean data only, no Docker teardown ──
if [ "$1" = "--skip-docker" ]; then
    echo "=========================================="
    echo "  SOFT RESET - Pizzeria El Gordo"
    echo "  (clean data + reimport, Docker stays up)"
    echo "=========================================="
    "$SCRIPT_DIR/clean-data.sh"
    "$SCRIPT_DIR/import-data.sh"
    echo ""
    echo "=========================================="
    echo "  SOFT RESET COMPLETE!"
    echo "=========================================="
    exit 0
fi

# ── Full nuclear path: destroy volumes, fresh start ────────
echo "=========================================="
echo "  NUCLEAR RESET - Pizzeria El Gordo"
echo "=========================================="
cd "$SCRIPT_DIR/.."

echo ""
echo "[0/3] Stopping containers and removing all data volumes..."
docker compose down -v --remove-orphans
docker system prune -f

echo ""
echo "[1/3] Starting fresh + installing Odoo modules..."
docker compose up -d
echo "  Waiting for database to be ready (20s)..."
sleep 20
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i base,stock,mrp,point_of_sale,pos_restaurant,pos_kitchen_screen_odoo --stop-after-init

echo ""
echo "[2/3] Importing all data..."
"$SCRIPT_DIR/import-data.sh"

echo ""
echo "=========================================="
echo "  NUCLEAR RESET COMPLETE!"
echo "=========================================="
