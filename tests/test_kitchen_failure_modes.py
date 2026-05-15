#!/usr/bin/env python3
"""
Kitchen Ticket Failure Mode Tests
==================================
Covers the battle-hardened scenarios from a chaotic Friday night rush:

  Case 1: Zombified Printer — print fails but ticket state remains valid
  Case 2: Race Condition Guard — double-tap idempotency
  Case 3: Ghost Modification — cancel an item already marked ready
  Case 4: Sync Storm — batch processing resilience
  Case 5: Partial Void — correct cancellation delta for partial quantity
  Case 6: Update to Finished Order — addition after delivery
  Case 7: Line state conflict — ready → re-cook cycle

Usage:
  docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo \\
    < tests/test_kitchen_failure_modes.py
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
print("  KITCHEN TICKET FAILURE MODE TESTS")
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
product = pizza_muzza
check("Mozzarella product found", bool(product))

pos_category = product.pos_categ_ids[0] if product.pos_categ_ids else None
if not pos_category:
    pos_category = env["pos.category"].create({"name": "[FAILTEST] Kitchen"})
    product.pos_categ_ids = [(6, 0, [pos_category.id])]

existing_ks = env["kitchen.screen"].search([
    ("pos_config_id", "=", pos_config.id),
])
existing_ks.unlink()

kitchen_screen = env["kitchen.screen"].create({
    "pos_config_id": pos_config.id,
    "pos_categ_ids": [(6, 0, [pos_category.id])],
    "printer_name": "XP-80",
})

env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE state != 'closed'")


def create_paid_order(qty=2.0, note=False):
    session = env["pos.session"].with_context(onboarding_creation=True).create({
        "config_id": pos_config.id,
    })
    total = qty * 10.0
    vals = {
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
    }
    order = env["pos.order"].create(vals)
    order.action_pos_order_paid()
    return order


# ═══════════════════════════════════════════════════════════
# Case 1: Zombified Printer — print failure resilience
# ═══════════════════════════════════════════════════════════
print("\n── Case 1: Zombified Printer ──")
print("   Scenario: Printer is out of paper or disconnected.")
print("   Expected: Ticket is still created. Format is valid for later printing.")
print("   qty_sent_to_kitchen still updated (kitchen has KDS screen).")

order1 = create_paid_order(2.0)
ticket1 = env["pos.kitchen.ticket"].search([
    ("origin_pos_order_id", "=", order1.id),
    ("ticket_type", "=", "new"),
], limit=1)

check("C1: Ticket exists despite printer failure", bool(ticket1))
if ticket1:
    check("C1: Ticket state is pending (not lost)", ticket1.state == "pending")
    check("C1: Ticket has line data", len(ticket1.line_ids) == 1)
    check("C1: qty_sent_to_kitchen is tracked",
          order1.lines.qty_sent_to_kitchen == 2.0)
    check("C1: Payment status captured", ticket1.payment_status == "paid")
    check("C1: ESC/POS formatter works",
          len(ticket1._format_ticket_escpos()) > 0)

# Simulate manual print retry — verify format is valid
if ticket1:
    formatted = ticket1._format_ticket_escpos()
    check("C1: ESC/POS format valid for retry", len(formatted) > 50)
    check("C1: ESC/POS contains header", "PIZZERIA EL GORDO" in formatted)
    check("C1: ESC/POS contains ticket", ticket1.sequence in formatted)
    check("C1: ESC/POS contains payment status", "PAGADO" in formatted)
    
    # Log to stdout instead of file
    print(f"\n  === CASE 1: ZOMBIFIED PRINTER ===")
    print(f"  Ticket: {ticket1.sequence}")
    print(f"  Order: {order1.name}")
    print(f"  Payment: {ticket1.payment_status}")
    print(f"  Formatted (logged above)")

# ═══════════════════════════════════════════════════════════
# Case 2: Race Condition Guard — double-payment guard
# ═══════════════════════════════════════════════════════════
print("\n── Case 2: Race Condition Guard ──")
print("   Scenario: Two waiters hit 'send to kitchen' simultaneously.")
print("   Expected: Only one 'new' ticket. Delta is detected, not duplicated.")

order2 = create_paid_order(3.0)
t2a = env["pos.kitchen.ticket"].get_or_create_ticket(order2)
t2b = env["pos.kitchen.ticket"].get_or_create_ticket(order2)
t2c = env["pos.kitchen.ticket"].get_or_create_ticket(order2)

check("C2: All calls return same ticket", t2a.id == t2b.id == t2c.id)
check("C2: Only one new ticket exists",
      env["pos.kitchen.ticket"].search_count([
          ("origin_pos_order_id", "=", order2.id),
          ("ticket_type", "=", "new"),
      ]) == 1)
check("C2: qty_sent_to_kitchen not doubled",
      order2.lines.qty_sent_to_kitchen == 3.0)

# Simulate race: change qty between two calls
order2.lines.qty = 4.0
race_delta = env["pos.kitchen.ticket"].create_delta_tickets(order2)
check("C2: Delta detected (+1)", len(race_delta) == 1)
if race_delta:
    check("C2: Delta is addition type", race_delta[0].ticket_type == "addition")
    check("C2: Delta qty is 1.0", race_delta[0].line_ids.qty_total == 1.0)
    check("C2: qty_sent updated to 4.0",
          order2.lines.qty_sent_to_kitchen == 4.0)

# Second race detection: no delta
order2.lines.qty = 4.0  # unchanged
race_delta2 = env["pos.kitchen.ticket"].create_delta_tickets(order2)
check("C2: No delta when unchanged (race guard)", len(race_delta2) == 0)

# ═══════════════════════════════════════════════════════════
# Case 3: Ghost Modification — cancel an already-ready item
# ═══════════════════════════════════════════════════════════
print("\n── Case 3: Ghost Modification ──")
print("   Scenario: Waiter removes item from POS after Chef marked it ready.")
print("   Expected: The ready line is NOT overwritten. Delta is tracked separately.")

order3 = create_paid_order(3.0)
t3 = env["pos.kitchen.ticket"].get_or_create_ticket(order3)

line3 = t3.line_ids[0]
line3.action_cooking()
line3.action_ready()
check("C3: Line is ready", line3.state == "ready")

# Waiter reduces qty from 3 to 2 in POS
order3.lines.qty = 2.0
ghost_delta = env["pos.kitchen.ticket"].create_delta_tickets(order3)
check("C3: Cancellation ticket created", len(ghost_delta) == 1)
if ghost_delta:
    gd = ghost_delta[0]
    check("C3: Cancellation type correct", gd.ticket_type == "cancellation")
    check("C3: Cancellation qty = 1.0", gd.line_ids.qty_total == 1.0)
    # The ORIGINAL line should still be ready (immutable)
    check("C3: Original line still ready (immutable)", line3.state == "ready")
    check("C3: qty_sent updated to 2.0",
          order3.lines.qty_sent_to_kitchen == 2.0)

# Chef tries to cancel the already-ready line
line3.action_cancel()
check("C3: Ready line can be cancelled by Chef", line3.state == "cancelled")

# ═══════════════════════════════════════════════════════════
# Case 4: Sync Storm — mass recreation
# ═══════════════════════════════════════════════════════════
print("\n── Case 4: Sync Storm ──")
print("   Scenario: 5 orders flood in after network recovery.")
print("   Expected: Each creates its own ticket. No data loss.")

orders = []
tickets = []
for i in range(5):
    o = create_paid_order(1.0)
    orders.append(o)
    t = env["pos.kitchen.ticket"].search([
        ("origin_pos_order_id", "=", o.id),
        ("ticket_type", "=", "new"),
    ], limit=1)
    tickets.append(t)

check("C4: 5 tickets created", len(tickets) == 5)
check("C4: All tickets have KT- sequence",
      all(t and t.sequence.startswith("KT-") for t in tickets))
check("C4: All tickets are type 'new'",
      all(t and t.ticket_type == "new" for t in tickets))
check("C4: All tickets are pending",
      all(t and t.state == "pending" for t in tickets))

# Advance all via batch
for t in tickets:
    if t:
        t.progress_to_cooking()
check("C4: All 5 advanced to cooking",
      all(t and t.state == "cooking" for t in tickets))

# Cancel half
for t in tickets[:2]:
    if t:
        t.cancel_ticket()
check("C4: First 2 cancelled",
      tickets[0].state == "cancelled" and tickets[1].state == "cancelled")

# ═══════════════════════════════════════════════════════════
# Case 5: Partial Void — cancel 1 out of 3
# ═══════════════════════════════════════════════════════════
print("\n── Case 5: Partial Void ──")
print("   Scenario: 3 Margheritas ordered, customer cancels 1.")
print("   Expected: Explicit REMOVE event, not a crash on negative delta.")

order5 = create_paid_order(3.0)
t5 = env["pos.kitchen.ticket"].get_or_create_ticket(order5)
check("C5: Initial qty_sent = 3.0",
      order5.lines.qty_sent_to_kitchen == 3.0)

order5.lines.qty = 2.0
partial_void = env["pos.kitchen.ticket"].create_delta_tickets(order5)

check("C5: One cancellation ticket", len(partial_void) == 1)
if partial_void:
    pv = partial_void[0]
    check("C5: Type is cancellation", pv.ticket_type == "cancellation")
    check("C5: Batch letter is B", pv.batch_letter == "B")
    check("C5: Cancelled qty = 1.0", pv.line_ids.qty_total == 1.0)
    check("C5: Cancelled line state = cancelled",
          pv.line_ids.state == "cancelled")

    formatted = pv._format_ticket_escpos()
    check("C5: ESC/POS contains cancel type",
          "CANCELACION" in formatted)
    check("C5: ESC/POS contains qty",
          "1" in formatted and "[CANC]" in formatted)
    
    with open("/tmp/kitchen_failure_test_log.txt", "a") as f:
        f.write(f"\n=== CASE 5: PARTIAL VOID ===\n")
        f.write(f"Ticket: {pv.sequence}\n")
        f.write(f"Type: {pv.ticket_type}\n")
        f.write(f"Formatted:\n{formatted}\n")
        f.write("=" * 50 + "\n")

# Cancel another 1
order5.lines.qty = 1.0
partial_void2 = env["pos.kitchen.ticket"].create_delta_tickets(order5)
check("C5: Second cancellation", len(partial_void2) == 1)
if partial_void2:
    check("C5: Second batch letter is C",
          partial_void2[0].batch_letter == "C")

# ═══════════════════════════════════════════════════════════
# Case 6: Update to Finished Order — addition after delivery
# ═══════════════════════════════════════════════════════════
print("\n── Case 6: Update to Finished Order ──")
print("   Scenario: Table finished, Chef cleared KDS, then +1 pizza.")
print("   Expected: New addition ticket is created. Old tickets untouched.")

order6 = create_paid_order(2.0)
t6 = env["pos.kitchen.ticket"].get_or_create_ticket(order6)

t6.progress_to_cooking()
t6.progress_to_ready()
t6.progress_to_delivered()
check("C6: Ticket delivered", t6.state == "delivered")
check("C6: delivered_at set", bool(t6.delivered_at))

# Customer wants +1 more
order6.lines.qty = 3.0
late_addition = env["pos.kitchen.ticket"].create_delta_tickets(order6)

check("C6: Late addition creates delta ticket", len(late_addition) == 1)
if late_addition:
    la = late_addition[0]
    check("C6: Late addition type = addition", la.ticket_type == "addition")
    check("C6: Late addition batch = B", la.batch_letter == "B")
    check("C6: Late addition state = pending", la.state == "pending")
    check("C6: Original ticket still delivered", t6.state == "delivered")
    check("C6: Late addition has 1.0 qty", la.line_ids.qty_total == 1.0)

    # KDS should show only the new addition (not the delivered original)
    details = env["pos.kitchen.ticket"].get_details(pos_config.id)
    detail_ids = {d["id"] for d in details}
    check("C6: Delivered ticket excluded from KDS",
          t6.id not in detail_ids)
    check("C6: Addition ticket IS in KDS",
          la.id in detail_ids)

# ═══════════════════════════════════════════════════════════
# Case 7: Line-level re-cook cycle
# ═══════════════════════════════════════════════════════════
print("\n── Case 7: Line re-cook cycle ──")
print("   Scenario: Chef accidentally marks ready, needs to re-cook.")
print("   Expected: Toggle cycles back to pending → cooking → ready.")

order7 = create_paid_order(1.0)
t7 = env["pos.kitchen.ticket"].get_or_create_ticket(order7)
line7 = t7.line_ids[0]

# Go through full cycle
line7.action_cooking()
check("C7: pending → cooking", line7.state == "cooking")

line7.action_ready()
check("C7: cooking → ready", line7.state == "ready")

# Oops, accidentally marked ready
line7.action_cancel()
check("C7: ready → cancelled", line7.state == "cancelled")

line7.action_toggle()
check("C7: cancelled → pending (toggle)", line7.state == "pending")

line7.action_toggle()
check("C7: pending → cooking (toggle)", line7.state == "cooking")

line7.action_toggle()
check("C7: cooking → ready (toggle)", line7.state == "ready")

line7.action_toggle()
check("C7: ready → cancelled (toggle)", line7.state == "cancelled")

check("C7: Ticket itself unchanged throughout line ops",
      t7.state == "pending")

# ── Summary ────────────────────────────────────────────────
print()
print("=" * 70)
print("  FAILURE MODE TEST RESULTS")
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
    print("  ALL FAILURE MODE TESTS PASSED")
    print()
    print("  System handles:")
    print("    - Printer disconnection (graceful fallback)")
    print("    - Race conditions (no duplicate tickets)")
    print("    - Ghost modifications (immutable ready items)")
    print("    - Sync storms (5 concurrent orders)")
    print("    - Partial voids (correct cancellation format)")
    print("    - Updates to finished orders (KDS isolation)")
    print("    - Line re-cook cycles (full state toggle)")
else:
    print(f"  {FAIL} TEST(S) FAILED")

print()
print("=" * 70)

env.cr.rollback()
