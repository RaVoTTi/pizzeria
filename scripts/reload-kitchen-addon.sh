#!/bin/bash
set -e

echo "=========================================="
echo "  Reloading POS Kitchen Screen Addon"
echo "=========================================="
cd "$(dirname "$0")/.."

echo ""
echo "[1/3] Upgrading module pos_kitchen_screen_odoo..."
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -u pos_kitchen_screen_odoo --stop-after-init

echo ""
echo "[2/3] Restarting web container..."
docker compose restart web

echo ""
echo "[3/3] Waiting for Odoo to be ready (10s)..."
sleep 10

echo ""
echo "=========================================="
echo "  Kitchen Screen addon reloaded!"
echo "  Open http://elgordo.local and test."
echo "=========================================="