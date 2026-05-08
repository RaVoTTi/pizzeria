#!/bin/bash
set -e

echo "=========================================="
echo "  CLEAN DATA - Pizzeria El Gordo"
echo "  Removes all imported data from the DB"
echo "  without touching Docker containers."
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/clean_data.py

echo ""
echo "=========================================="
echo "  Data clean complete!"
echo "  Run scripts/import-data.sh to reload."
echo "=========================================="
