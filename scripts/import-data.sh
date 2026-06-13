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
echo "[1/14] Installing Odoo modules if needed + UoMs..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py

echo ""
echo "[2/14] Creating product categories..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_01_categories.py

echo ""
echo "[3/14] Creating ingredients, drinks, delivery, and Bollo..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_02_ingredients.py

echo ""
echo "[4/14] Creating saleable products (pizzas, mitades, empanadas)..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_03_products.py

echo ""
echo "[5/14] Creating Bill of Materials..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_04_boms.py

echo ""
echo "[6/14] Setting up POS categories..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_05_pos.py

echo ""
echo "[7/14] Setting up restaurant floor plans..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py

echo ""
echo "[8/14] Setting language to Spanish..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/set_language_spanish.py

echo ""
echo "[9/14] Setting timezone to Argentina..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_timezone.py

echo ""
echo "[10/14] Creating users from CSV..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_users.py

echo ""
echo "[11/14] Removing taxes from products..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/remove_taxes.py

echo ""
echo "[12/14] Loading initial stock quantities..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_test_inventory.py

echo ""
echo "[13/14] Setting up Mercado Pago terminal..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_mercado_pago.py

echo ""
echo "[14/14] Setting up POS Kitchen Screen..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_kitchen_display.py

echo ""
echo "  Setting company logo..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_company_logo.py

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
echo "              [S] Paninis, [S] Postres, Paninis, Postres,"
echo "              Cerveza, Bebidas, Empanadas, Pizzas, Mitades, Delivery"
echo "  18 Tables with floor plan"
echo "  Spanish language, Argentina timezone, no taxes"
echo "  Users from employees.csv with POS PINs"
echo "  Company logo set"
echo "  Initial stock loaded"
echo ""
echo "  Access: http://elgordo.local"
echo "=========================================="
