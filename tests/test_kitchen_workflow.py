#!/usr/bin/env python3
"""
Kitchen Ticket Complete Workflow Test
=====================================
End-to-end test of the kitchen ticket lifecycle:

  1. POS order creation → kitchen ticket auto-generation
  2. Ticket state progression (pending → cooking → ready → delivered)
  3. Per-line state toggles (pending → cooking → ready → cancelled)
  4. Delta tickets: additions and cancellations with batch letters
  5. qty_sent_to_kitchen tracking
  6. Idempotency (no duplicate new tickets)
  7. get_details() filtering
  8. Printer method (graceful failure test)

Usage:
  docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo \\
    < tests/test_kitchen_workflow.py
"""

import json

PASS = 0
FAIL = 0
ERRORS = []


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS [{label}]")
    else:
        FAIL += 1
        msg = f"  FAIL [{label}] {detail}"
        print(msg)
        ERRORS.append(msg)


print("=" * 70)
print("  KITCHEN TICKET COMPLETE WORKFLOW TEST")
print("=" * 70)

# ── Test Setup ─────────────────────────────────────────────
print("\n── Test Setup ──")

company = env.ref("base.main_company", raise_if_not_found=False)
if not company:
    company = env["res.company"].search([], limit=1)

pos_config = env["pos.config"].search([], limit=1)
check("POS config exists", bool(pos_config))
if not pos_config:
    print("FATAL: No POS config. Run import-data.sh first.")
    exit(1)

partner = env["res.partner"].create({"name": "Test Customer"})

pizza_muzza = env["product.product"].search([("name", "=", "Mozzarella")], limit=1)
if not pizza_muzza:
    pizza_muzza = env["product.product"].search([("name", "ilike", "Mozzarella")], limit=1)
check("Mozzarella product found", bool(pizza_muzza))
product = pizza_muzza

pos_category = product.pos_categ_ids[0] if product.pos_categ_ids else None
if not pos_category:
    pos_category = env["pos.category"].create({"name": "[TEST] Kitchen Category"})
    product.pos_categ_ids = [(6, 0, [pos_category.id])]
check("Product has POS category", bool(pos_category))

existing_ks = env["kitchen.screen"].search([
    ("pos_config_id", "=", pos_config.id),
])
existing_ks.unlink()

kitchen_screen = env["kitchen.screen"].create({
    "pos_config_id": pos_config.id,
    "pos_categ_ids": [(6, 0, [pos_category.id])],
    "printer_name": "XP-80",
})
check("Kitchen screen created", bool(kitchen_screen))

env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE state != 'closed'")


def create_paid_order(qty=2.0):
    session = env["pos.session"].with_context(onboarding_creation=True).create({
        "config_id": pos_config.id,
    })
    total = qty * 10.0
    order = env["pos.order"].create({
        "company_id": company.id,
        "session_id": session.id,
        "partner_id": partner.id,
        "pricelist_id": pos_config.pricelist_id.id,
        "config_id": pos_config.id,
        "amount_tax": 0.0,
        "amount_total": total,
        "amount_paid": total,
        "amount_return": 0.0,
        "lines": [(0, 0, {
            "product_id": product.id,
            "qty": qty,
            "price_unit": 10.0,
            "price_subtotal": total,
            "price_subtotal_incl": total,
        })],
    })
    order.action_pos_order_paid()
    return order


# ── Test 1: Ticket creation on payment ─────────────────────
print("\n── Test 1: Auto-creation on payment ──")

order = create_paid_order(2.0)
ticket = env["pos.kitchen.ticket"].search([
    ("origin_pos_order_id", "=", order.id),
    ("ticket_type", "=", "new"),
], limit=1)

check("Ticket created on payment", bool(ticket))
check("Ticket type is 'new'", ticket.ticket_type == "new" if ticket else False)
check("Ticket state is 'pending'", ticket.state == "pending" if ticket else False)
check("Ticket payment_status is 'paid'", ticket.payment_status == "paid" if ticket else False)
check("Batch letter is A", ticket.batch_letter == "A" if ticket else False)
check("Sequence starts with KT-", ticket.sequence.startswith("KT-") if ticket else False)
check("One line created", len(ticket.line_ids) == 1 if ticket else False)
check("Line qty_total = 2.0", ticket.line_ids.qty_total == 2.0 if ticket else False)
check("Line qty_sent = 2.0", ticket.line_ids.qty_sent == 2.0 if ticket else False)
check("Line state is pending", ticket.line_ids.state == "pending" if ticket else False)
check("qty_sent_to_kitchen = 2.0",
      order.lines.qty_sent_to_kitchen == 2.0 if ticket else False)

# ── Test 2: Ticket idempotency ─────────────────────────────
print("\n── Test 2: Idempotency (no duplicates) ──")

order.action_pos_order_paid()
order.action_pos_order_paid()
new_tickets = env["pos.kitchen.ticket"].search([
    ("origin_pos_order_id", "=", order.id),
    ("ticket_type", "=", "new"),
])
check("Only one 'new' ticket exists", len(new_tickets) == 1,
      f"found {len(new_tickets)}")

# ── Test 3: Line state cycle ───────────────────────────────
print("\n── Test 3: Line state lifecycle ──")

line = ticket.line_ids[0]
check("Line starts pending", line.state == "pending")

line.action_cooking()
check("Line → cooking", line.state == "cooking")

line.action_ready()
check("Line → ready", line.state == "ready")

line.action_cancel()
check("Line → cancelled", line.state == "cancelled")

line.action_toggle()
check("Line → pending (toggle loop)", line.state == "pending")

# ── Test 4: Ticket state progression ───────────────────────
print("\n── Test 4: Ticket state progression ──")

check("Ticket starts pending", ticket.state == "pending")

ticket.progress_to_cooking()
check("Ticket → cooking", ticket.state == "cooking")
check("started_at populated", bool(ticket.started_at))

ticket.progress_to_ready()
check("Ticket → ready", ticket.state == "ready")
check("ready_at populated", bool(ticket.ready_at))
check("All lines marked ready", all(l.state == "ready" for l in ticket.line_ids))

ticket.progress_to_delivered()
check("Ticket → delivered", ticket.state == "delivered")
check("delivered_at populated", bool(ticket.delivered_at))

# Reset for next tests
ticket.line_ids.write({"state": "pending"})
ticket.state = "pending"

# ── Test 5: Delta addition ticket ──────────────────────────
print("\n── Test 5: Delta addition ──")

order2 = create_paid_order(2.0)
t2 = env["pos.kitchen.ticket"].search([
    ("origin_pos_order_id", "=", order2.id),
    ("ticket_type", "=", "new"),
], limit=1)
check("Initial qty_sent_to_kitchen = 2.0",
      order2.lines.qty_sent_to_kitchen == 2.0)

order2.lines.qty = 3.0
delta_tickets = env["pos.kitchen.ticket"].create_delta_tickets(order2)

check("One delta ticket created", len(delta_tickets) == 1,
      f"got {len(delta_tickets)}")
if delta_tickets:
    dt = delta_tickets[0]
    check("Delta ticket type = addition", dt.ticket_type == "addition")
    check("Batch letter = B", dt.batch_letter == "B")
    check("Delta qty_total = 1.0", dt.line_ids.qty_total == 1.0)
    check("qty_sent_to_kitchen updated to 3.0",
          order2.lines.qty_sent_to_kitchen == 3.0)

# ── Test 6: Delta cancellation ticket ──────────────────────
print("\n── Test 6: Delta cancellation ──")

order3 = create_paid_order(3.0)
t3 = env["pos.kitchen.ticket"].get_or_create_ticket(order3)
check("qty_sent_to_kitchen = 3.0",
      order3.lines.qty_sent_to_kitchen == 3.0)

order3.lines.qty = 1.0
cancel_tickets = env["pos.kitchen.ticket"].create_delta_tickets(order3)

check("One cancellation delta created", len(cancel_tickets) == 1,
      f"got {len(cancel_tickets)}")
if cancel_tickets:
    ct = cancel_tickets[0]
    check("Delta type = cancellation", ct.ticket_type == "cancellation")
    check("Batch letter = B", ct.batch_letter == "B")
    check("Cancellation qty = 2.0", ct.line_ids.qty_total == 2.0)
    check("Cancellation line state = cancelled",
          ct.line_ids.state == "cancelled")
    check("qty_sent_to_kitchen = 1.0",
          order3.lines.qty_sent_to_kitchen == 1.0)

# ── Test 7: Multiple deltas with batch letters ─────────────
print("\n── Test 7: Sequential batch letters ──")

order4 = create_paid_order(2.0)
t4 = env["pos.kitchen.ticket"].get_or_create_ticket(order4)

order4.lines.qty = 3.0
d1 = env["pos.kitchen.ticket"].create_delta_tickets(order4)
check("Batch B", d1[0].batch_letter == "B" if d1 else False)

order4.lines.qty = 4.0
d2 = env["pos.kitchen.ticket"].create_delta_tickets(order4)
check("Batch C", d2[0].batch_letter == "C" if d2 else False)

order4.lines.qty = 2.0
d3 = env["pos.kitchen.ticket"].create_delta_tickets(order4)
check("Batch D (cancellation)", d3[0].batch_letter == "D" if d3 else False)
check("Batch D is cancellation", d3[0].ticket_type == "cancellation" if d3 else False)

# ── Test 8: No delta when unchanged ────────────────────────
print("\n── Test 8: No delta when unchanged ──")

order5 = create_paid_order(2.0)
env["pos.kitchen.ticket"].get_or_create_ticket(order5)
no_delta = env["pos.kitchen.ticket"].create_delta_tickets(order5)
check("No delta tickets created", len(no_delta) == 0,
      f"got {len(no_delta)}")

# ── Test 9: get_details filtering ──────────────────────────
print("\n── Test 9: get_details() filtering ──")

details = env["pos.kitchen.ticket"].get_details(pos_config.id)
active_ids = {d["id"] for d in details}
check("Active tickets returned", t4.id in active_ids)

t4.cancel_ticket()
details2 = env["pos.kitchen.ticket"].get_details(pos_config.id)
check("Cancelled ticket excluded from get_details",
      t4.id not in {d["id"] for d in details2})

# ── Test 10: ESC/POS format verification ──────────────────
print("\n── Test 10: ESC/POS ticket format ──")

order6 = create_paid_order(1.0)
t6 = env["pos.kitchen.ticket"].search([
    ("origin_pos_order_id", "=", order6.id),
    ("ticket_type", "=", "new"),
], limit=1)

if t6:
    formatted = t6._format_ticket_escpos()
    check("ESC/POS format generates content", len(formatted) > 50)
    check("ESC/POS contains header", "PIZZERIA EL GORDO" in formatted)
    check("ESC/POS contains ticket sequence", t6.sequence in formatted)
    check("ESC/POS contains payment status", "PAGADO" in formatted or "NO PAGADO" in formatted)

    print(f"\n  --- Would print to {kitchen_screen.printer_name} ---")
    print(f"  --- Formatted ticket (logged below) ---")
    print(f"  Payment Status: {t6.payment_status}")
    
    print(f"\n=== TICKET {t6.sequence} ===")
    print(f"Order: {order6.name}")
    print(f"Type: {t6.ticket_type}")
    print(f"State: {t6.state}")
    print(f"Payment: {t6.payment_status}")
    print(f"Formatted:")
    print(formatted)
    print("=" * 50)

# ── Test 11: Line note preservation ────────────────────────
print("\n── Test 11: Note preservation ──")

session_note = env["pos.session"].with_context(onboarding_creation=True).create({
    "config_id": pos_config.id,
})
total_note = 10.0
order7 = env["pos.order"].create({
    "company_id": company.id,
    "session_id": session_note.id,
    "partner_id": partner.id,
    "pricelist_id": pos_config.pricelist_id.id,
    "config_id": pos_config.id,
    "amount_tax": 0.0,
    "amount_total": total_note,
    "amount_paid": total_note,
    "amount_return": 0.0,
    "lines": [(0, 0, {
        "product_id": product.id,
        "qty": 1.0,
        "price_unit": 10.0,
        "price_subtotal": total_note,
        "price_subtotal_incl": total_note,
        "note": "Sin aceitunas",
    })],
})
order7.action_pos_order_paid()

t7 = env["pos.kitchen.ticket"].get_or_create_ticket(order7)
check("Note persists in ticket line",
      t7.line_ids.note == "Sin aceitunas" if t7 else False)

# ── Summary ────────────────────────────────────────────────
print()
print("=" * 70)
print("  TEST RESULTS")
print("=" * 70)
print(f"  Passed: {PASS}")
print(f"  Failed: {FAIL}")
if ERRORS:
    print()
    print("  Errors:")
    for e in ERRORS:
        print(f"    - {e}")

print()
if FAIL == 0:
    print("  ALL KITCHEN TICKET TESTS PASSED")
else:
    print(f"  {FAIL} TEST(S) FAILED")

print()
print("=" * 70)

env.cr.rollback()
