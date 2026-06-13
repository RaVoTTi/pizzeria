#!/bin/bash
set -e

echo "=========================================="
echo "  UPDATE PRICES & PRODUCTS"
echo "  Pizzeria El Gordo"
echo "  Updates prices, adds paninis, docenas,"
echo "  and postres category."
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

echo ""
echo "[1/5] Updating categories (adding Paninis, Postres)..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_01_categories.py

echo ""
echo "[2/5] Updating ingredients/beverages prices..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_02_ingredients.py

echo ""
echo "[3/5] Updating product prices + adding paninis, docenas..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_03_products.py

echo ""
echo "[4/5] Updating BoMs for new salon products..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_04_boms.py

echo ""
echo "[5/5] Updating POS categories (adding Paninis)..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_05_pos.py

echo ""
echo "  Restarting containers..."
docker compose restart web

echo ""
echo "=========================================="
echo "  UPDATE COMPLETE!"
echo "=========================================="
echo ""
echo "  Updated prices:"
echo "    - Pizzas Mostrador (new prices)"
echo "    - Bebidas (gaseosas 2.25L → \$7000,"
echo "      aguas → \$3500, pintas → \$7000,"
echo "      recargas 1L → \$10000)"
echo ""
echo "  New products:"
echo "    - Panini Clásico, Caprese, del Gordo"
echo "    - [S] Panini variants"
echo "    - ½ Docena Empanadas (5 sabores)"
echo "    - [S] ½ Docena Empanadas"
echo "    - Docena Empanadas (5 sabores)"
echo "    - [S] Docena Empanadas"
echo "    - Cerveza 710 ml"
echo ""
echo "  New categories:"
echo "    - Paninis"
echo "    - Postres"
echo ""
echo "  Access: http://elgordo.local"
echo "=========================================="
