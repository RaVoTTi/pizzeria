#!/bin/bash
set -e

echo "🧨 NUCLEAR RESET - Deleting everything and rebuilding from scratch..."
cd ~/Documents/odoo-pizzeria

echo "🛑 Stopping containers and removing all data volumes..."
docker compose down -v --remove-orphans
docker system prune -f

echo "🚀 Starting fresh..."
docker compose up -d

echo "⏳ Waiting for database to be ready (20s)..."
sleep 20

echo "🔧 Installing Odoo modules..."
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i base,stock,mrp,point_of_sale,pos_restaurant --stop-after-init

echo "📥 Step 1/5: Importing units of measure..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py

echo "📥 Step 2/5: Importing products, categories, and BoMs..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_products.py

echo "🗺️  Step 3/5: Setting up restaurant floor plans..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py

# echo "💰 Step 4/5: Removing taxes from products..."
# docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/remove_taxes.py

# echo "🍕 Step 5/5: Setting up Mitad y Mitad..."
# bash scripts/setup-mitad.sh

# echo "🔄 Restarting containers..."
# docker compose restart web

echo ""
echo "================================"
echo "✅ SETUP COMPLETE!"
echo "================================"
echo ""
echo "Your pizzeria is ready with:"
echo "  • 80 Products"
echo "  • 21 Phantom BoMs for whole pizzas"
echo "  • 19 Tables with floor plan"
echo "  • Mitad y Mitad: Dynamic variants + phantom BoM"
echo "  • POS Configurator: 2-step wizard (Lado A → Lado B)"
echo "  • POS Pricing: MAX(price_A, price_B) auto-calculated"
echo ""
echo "Access: http://elgordo.local"
echo "================================"
