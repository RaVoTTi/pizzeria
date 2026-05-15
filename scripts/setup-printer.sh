#!/bin/bash
set -e

echo "=========================================="
echo "  Kitchen Printer Setup"
echo "=========================================="
cd "$(dirname "$0")/.."

echo ""
echo "[1/4] Checking CUPS socket on host..."
if [ -S /var/run/cups/cups.sock ]; then
    echo "  CUPS socket found at /var/run/cups/cups.sock"
else
    echo "  ERROR: CUPS socket not found. Is CUPS installed and running?"
    echo "  Install with: sudo apt-get install cups"
    echo "  Then configure your printer: http://localhost:631"
    exit 1
fi

echo ""
echo "[2/4] Building Odoo image with CUPS client..."
docker compose build web

echo ""
echo "[3/4] Restarting web container with printer mount..."
docker compose up -d web
echo "  Waiting for Odoo to be ready (10s)..."
sleep 10

echo ""
echo "[4/4] Testing printer from Docker..."
docker exec pizzeria-web-1 bash -c 'echo "=== PIZZERIA EL GORDO ===" | lp -d XP-80 2>&1' && \
    echo "  Printer test sent successfully!" || \
    echo "  WARNING: Print test failed. Check printer name in CUPS."

echo ""
echo "=========================================="
echo "  Printer setup complete!"
echo "=========================================="
echo ""
echo "  Printer:        XP-80 (via CUPS)"
echo "  Socket mounted: /var/run/cups/cups.sock"
echo "  cups-client:    installed in web container"
echo ""
echo "  To change the printer name:"
echo "  1. Go to Point of Sale > Pos kitchen screen"
echo "  2. Edit your Kitchen Screen record"
echo "  3. Change 'Nombre de Impresora' field"
echo ""
echo "  To test printing from the kitchen screen:"
echo "  1. Create a POS order with kitchen-category products"
echo "  2. Pay the order"
echo "  3. A kitchen ticket should print automatically"
echo "=========================================="
