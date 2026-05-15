#!/bin/bash
set -e

DB_NAME="elgordo"
CONTAINER_NAME="web"

echo "=============================================="
echo "  Generate Test POS Order - Pizzeria El Gordo"
echo "=============================================="
echo ""

docker compose run --rm -T $CONTAINER_NAME odoo shell -d $DB_NAME <<EOF
# ── Configuration ────────────────────────────────────────
import json
from datetime import datetime

LOG_FILE = "/tmp/pos_order_log.txt"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} - {msg}\n")
    print(msg)

# ── Find POS Config ──────────────────────────────────────
pos_config = env["pos.config"].search([], limit=1)
if not pos_config:
    log("FATAL: No POS config found")
    exit(1)

log(f"Using POS: {pos_config.name} (ID: {pos_config.id})")

# ── Find or Create Partner ───────────────────────────────
partner = env["res.partner"].search([("name", "=", "Test Customer")], limit=1)
if not partner:
    partner = env["res.partner"].create({"name": "Test Customer"})
    log(f"Created partner: {partner.name}")
else:
    log(f"Using partner: {partner.name}")

# ── Find Real Pizza Product ──────────────────────────────
pizza = env["product.product"].search([("name", "=", "Mozzarella")], limit=1)
if not pizza:
    pizza = env["product.product"].search([("name", "ilike", "Mozzarella")], limit=1)
if not pizza:
    log("FATAL: Mozzarella pizza not found. Run import-data.sh first.")
    exit(1)

log(f"Using product: {pizza.name} (ID: {pizza.id}, Price: {pizza.list_price})")

# ── Close Old Sessions ───────────────────────────────────
env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE state != 'closed'")
log("Closed any open sessions")

# ── Create New Session ───────────────────────────────────
session = env["pos.session"].with_context(onboarding_creation=True).create({
    "config_id": pos_config.id,
})
log(f"Created session: {session.name} (ID: {session.id})")

# ── Get Payment Method ───────────────────────────────────
payment_method = env["pos.payment.method"].search([
    ("is_cash_count", "=", True),
], limit=1)
if not payment_method:
    payment_method = env["pos.payment.method"].search([], limit=1)
log(f"Using payment method: {payment_method.name}")

# ── Create POS Order ─────────────────────────────────────
qty = 2.0
total = qty * pizza.list_price

order = env["pos.order"].create({
    "company_id": pos_config.company_id.id,
    "session_id": session.id,
    "partner_id": partner.id,
    "pricelist_id": pos_config.pricelist_id.id,
    "config_id": pos_config.id,
    "amount_tax": 0.0,
    "amount_total": total,
    "amount_paid": total,
    "amount_return": 0.0,
    "lines": [(0, 0, {
        "product_id": pizza.id,
        "qty": qty,
        "price_unit": pizza.list_price,
        "price_subtotal": total,
        "price_subtotal_incl": total,
        "full_product_name": pizza.name,
    })],
})

log(f"Created order: {order.name} (ID: {order.id})")

# ── Process Payment ──────────────────────────────────────
order.action_pos_order_paid()
log(f"Order {order.name} marked as PAID")

# ── Verify Kitchen Ticket ────────────────────────────────
ticket = env["pos.kitchen.ticket"].search([
    ("origin_pos_order_id", "=", order.id),
    ("ticket_type", "=", "new"),
], limit=1)

if ticket:
    log(f"✓ Kitchen ticket created: {ticket.sequence}")
    log(f"  Type: {ticket.ticket_type}")
    log(f"  State: {ticket.state}")
    log(f"  Batch: {ticket.batch_letter}")
    log(f"  Lines: {len(ticket.line_ids)}")
    
    for line in ticket.line_ids:
        log(f"    - {line.full_product_name}: {line.qty_total} (state: {line.state})")
    
    formatted = ticket._format_ticket_escpos()
    log(f"\n  --- Formatted Ticket ---")
    log(f"  Full ticket logged below:")
    log(f"\n{formatted}")
else:
    log("✗ WARNING: No kitchen ticket created!")

log(f"\n=============================================")
log(f"  ORDER GENERATION COMPLETE")
log(f"=============================================")
log(f"  Order: {order.name}")
log(f"  Ticket: {ticket.sequence if ticket else 'N/A'}")
log(f"  Log file: {LOG_FILE}")
log(f"=============================================\n")

env.cr.commit()
EOF

echo ""
echo "Done! Check /tmp/pos_order_log.txt for details"
echo "To view log: docker compose exec web cat /tmp/pos_order_log.txt"
