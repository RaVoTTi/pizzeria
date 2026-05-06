#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting Odoo shell..."
echo "Connected to database: elgordo"
echo ""
echo "Useful commands inside the shell:"
echo "  env['product.template'].search([])           # List all products"
echo "  env['product.category'].search([])            # List all categories"
echo "  env.ref('base.user_admin')                    # Reference to admin user"
echo "  self.env.cr.rollback()                        # Rollback changes"
echo "  self.env.cr.commit()                          # Commit changes"
echo ""

docker compose -f "$PROJECT_DIR/docker-compose.yml" run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo