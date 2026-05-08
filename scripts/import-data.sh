#!/bin/bash
set -e

echo "=========================================="
echo "  IMPORT DATA - Pizzeria El Gordo"
echo "  Imports all CSVs into the database."
echo "  Assumes Docker is already running."
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

echo ""
echo "[1/10] Installing Odoo modules if needed + UoMs..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py

echo ""
echo "[2/10] Creating product categories..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_01_categories.py

echo ""
echo "[3/10] Creating ingredients, drinks, delivery, and Bollo..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_02_ingredients.py

echo ""
echo "[4/10] Creating saleable products (pizzas, mitades, empanadas)..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_03_products.py

echo ""
echo "[5/10] Creating Bill of Materials..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_04_boms.py

echo ""
echo "[6/10] Setting up POS categories..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_05_pos.py

echo ""
echo "[7/10] Setting up restaurant floor plans..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py

echo ""
echo "[8/10] Setting language to Spanish..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/set_language_spanish.py

echo ""
echo "[9/10] Removing taxes from products..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/remove_taxes.py

echo ""
echo "[10/10] Loading initial stock quantities..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_test_inventory.py

echo ""
echo "  Running BoM validation diagnostic..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/validate_boms.py

echo ""
echo "  Restarting containers..."
docker compose restart web

echo ""
echo "=========================================="
echo "  IMPORT COMPLETE!"
echo "=========================================="
echo ""
echo "  Products: Mostrador + [S] Salon variants"
echo "  Phantom BoMs: [S] -> Mostrador -> ingredients"
echo "  Categories: [S] Empanadas, [S] Pizzas, [S] Mitades,"
echo "              Cerveza, Bebidas, Empanadas, Pizzas, Mitades, Delivery"
echo "  18 Tables with floor plan"
echo "  Spanish language, no taxes"
echo "  Initial stock loaded"
echo ""
echo "  Access: http://elgordo.local"
echo "=========================================="
