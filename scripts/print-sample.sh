#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

DEFAULT_PRINTER="${KITCHEN_PRINTER:-XP-80}"
SAMPLES_HOST="./addons/kitchen_samples"
PRINTER="$DEFAULT_PRINTER"
PRINT_ALL=false

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Generate sample kitchen tickets (ESC/POS .bin files) and optionally print."
    echo ""
    echo "Options:"
    echo "  --printer NAME   CUPS printer name (default: $DEFAULT_PRINTER)"
    echo "  --print          Print all generated samples to the printer"
    echo "  -h, --help       Show this help"
    echo ""
    echo "Samples are written to:"
    echo "  $SAMPLES_HOST/"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --printer) PRINTER="$2"; shift 2 ;;
        --print) PRINT_ALL=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

echo "=========================================="
echo "  Kitchen Ticket Sample Generator"
echo "=========================================="
echo ""

rm -rf "$SAMPLES_HOST"
docker compose rm -f kitchen-sample-gen 2>/dev/null || true

echo "[1/2] Generating samples..."
docker compose run --name kitchen-sample-gen web \
    odoo shell -c /etc/odoo/odoo.conf -d elgordo --no-http \
    < addons/generate_sample_ticket.py

echo ""
echo "[2/2] Copying files from container..."
docker cp kitchen-sample-gen:/tmp/kitchen_samples "$SAMPLES_HOST"
docker rm -f kitchen-sample-gen 2>/dev/null || true

echo ""
ls -lh "$SAMPLES_HOST/"

if $PRINT_ALL; then
    echo ""
    echo "Sending all samples to printer: $PRINTER"
    for f in "$SAMPLES_HOST"/*.bin; do
        echo "  $(basename "$f") -> $PRINTER"
        lp -d "$PRINTER" -o raw "$f" 2>&1 || echo "  WARNING: lp failed (printer $PRINTER may not exist)"
    done
else
    echo ""
    echo "To print a specific sample:"
    echo "  lp -d $PRINTER -o raw $SAMPLES_HOST/01_mesa_muzzarella.bin"
    echo ""
    echo "To print all samples:"
    echo "  $0 --print"
fi

echo ""
echo "To view human-readable content:"
echo "  cat $SAMPLES_HOST/01_mesa_muzzarella.bin | strings"
echo ""
echo "Done."
