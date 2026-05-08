#!/bin/bash
set -e

echo "=========================================="
echo "  NUCLEAR RESET - Pizzeria El Gordo"
echo "=========================================="
cd ~/Documents/odoo-pizzeria

echo ""
echo "[0/11] Stopping containers and removing all data volumes..."
docker compose down -v --remove-orphans
docker system prune -f

echo ""
echo "[0/11] Starting fresh..."
docker compose up -d

echo ""
echo "[0/11] Waiting for database to be ready (20s)..."
sleep 20

echo ""
echo "[1/11] Installing Odoo modules..."
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i base,stock,mrp,point_of_sale,pos_restaurant --stop-after-init

echo ""
echo "[2/11] Importing units of measure..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py

echo ""
echo "[3/11] Creating product categories..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_01_categories.py

echo ""
echo "[4/11] Creating ingredients, drinks, delivery, and Bollo..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_02_ingredients.py

echo ""
echo "[5/11] Creating saleable products (pizzas, mitades, empanadas)..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_03_products.py

echo ""
echo "[6/11] Creating Bill of Materials (ingredient recipes + Salon links)..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_04_boms.py

echo ""
echo "[7/11] Setting up POS categories..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_05_pos.py

echo ""
echo "[8/11] Setting up restaurant floor plans..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py

echo ""
echo "[9/11] Setting language to Spanish..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/set_language_spanish.py

echo ""
echo "[10/11] Removing taxes from products..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/remove_taxes.py

echo ""
echo "[11/11] Loading initial stock quantities..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_test_inventory.py

echo ""
echo "  Running BoM validation diagnostic..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/validate_boms.py

echo ""
echo "  Restarting containers..."
docker compose restart web

echo ""
echo "=========================================="
echo "  SETUP COMPLETE!"
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