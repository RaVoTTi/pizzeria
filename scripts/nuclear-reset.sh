#!/bin/bash
set -e

echo "🧨 NUCLEAR RESET - Deleting everything and rebuilding from scratch..."
cd ~/Documents/odoo-pizzeria

echo "📦 Creating backup just in case..."
./scripts/backup.sh 2>/dev/null || echo "⚠️  No backup script found, continuing without backup..."

echo "🛑 Stopping containers..."
docker compose down

echo "🗑️  Removing all data volumes (THIS DELETES ALL DATA!)..."
docker volume rm -f odoo-pizzeria_odoo-db-data odoo-pizzeria_odoo-web-data 2>/dev/null || true
docker system prune -f

echo "🚀 Starting fresh..."
docker compose up -d

echo "⏳ Waiting for database to be ready (20s)..."
sleep 20

echo "🔧 Installing Odoo modules (base, stock, mrp, point_of_sale, pos_restaurant)..."
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i base,stock,mrp,point_of_sale,pos_restaurant --stop-after-init

echo "📥 Step 1/3: Importing units of measure..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py

echo "📥 Step 2/3: Importing products, categories, and BoMs..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_products.py

echo "🗺️  Step 3/3: Setting up restaurant floor plans with images..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py

echo "🔄 Restarting web container..."
docker compose restart web

echo ""
echo "================================"
echo "✅ SETUP COMPLETE!"
echo "================================"
echo ""
echo "Your pizzeria is ready with:"
echo "  • 79 Products (pizzas, drinks, empanadas, ingredients)"
echo "  • 21 Phantom BoMs (auto-deduct ingredients)"
echo "  • 4 POS categories (Pizzas, Cerveza, Bebidas, Empanadas)"
echo "  • 19 Tables with floor plan images"
echo "    - Salón: tables 1-12"
echo "    - Afuera: tables 13-16 + 3 round tables"
echo ""
echo "Access: http://elgordo.local"
echo "Admin password: see config/odoo.conf"
echo ""
echo "NEXT STEPS:"
echo "1. Open browser to http://elgordo.local"
echo "2. Log in as admin"
echo "3. Set language to Spanish (Settings → Translations → Languages)"
echo "4. Open Point of Sale session"
echo "5. If images don't appear immediately, press Ctrl+Shift+R for hard refresh"
echo ""
echo "Demo products are hidden. Your products should appear in POS!"
echo "================================"
