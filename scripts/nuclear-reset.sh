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

echo "📥 Step 1/7: Importing units of measure..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py

echo "📥 Step 2/7: Importing products, categories, and BoMs..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_products.py

echo "🗺️  Step 3/7: Setting up restaurant floor plans..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py

echo "🌐 Step 4/7: Setting language to Spanish..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/set_language_spanish.py

echo "💰 Step 5/7: Removing taxes from products..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/remove_taxes.py

echo "📦 Step 6/7: Loading initial stock quantities..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_test_inventory.py

echo "🔄 Step 7/7: Restarting containers..."
docker compose restart web

echo ""
echo "================================"
echo "✅ SETUP COMPLETE!"
echo "================================"
echo ""
echo "Your pizzeria is ready with:"
echo "  • 99 Products (81 full + 18 halves)"
echo "  • 40 Phantom BoMs (21 whole pizzas + 18 halves + Bollo)"
echo "  • 18 Tables with floor plan"
echo "  • Spanish language"
echo "  • Taxes removed"
echo "  • Initial stock loaded"
echo ""
echo "Access: http://elgordo.local"
echo "================================"
