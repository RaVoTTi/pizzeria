#!/bin/bash
set -e

echo "🍕 MITAD Y MITAD SETUP"
echo "====================="
cd ~/Documents/odoo-pizzeria

echo "📦 Step 1/4: Installing Mitad y Mitad modules..."
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i pos_mitad_configurator,pos_half_pizza --stop-after-init

echo "🧹 Step 2/4: Cleaning up existing Mitad y Mitad configuration..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/mitad/complete_cleanup.py

echo "🔧 Step 3/4: Setting up Mitad y Mitad (dynamic variants + phantom BoM)..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/mitad/setup_mitad_mitad.py

echo "✅ Step 4/4: Verifying Mitad y Mitad configuration..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/mitad/debug_scripts/step6_verify.py

echo ""
echo "================================"
echo "🍕 MITAD Y MITAD SETUP COMPLETE"
echo "================================"
echo ""
echo "  18 pizza options per side (dynamic variants, 0 upfront)"
echo "  Phantom BoM: 1 dough + 112 conditional topping lines"
echo "  2-step tile wizard in POS (pos_mitad_configurator)"
echo "  MAX pricing (pos_half_pizza)"
echo ""
echo "  Test: http://elgordo.local --> POS --> 🍕 Mitad y Mitad"
echo "        Hard refresh (Ctrl+Shift+R) after first load"
echo "================================"
