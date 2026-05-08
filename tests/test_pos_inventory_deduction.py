"""
Phantom BoM Inventory Deduction Test

Simulates selling pizzas via POS and verifies that Odoo correctly
deducts raw ingredients through the phantom BoM chain:

  Pizza (phantom BoM) → Bollo de Masa + Toppings
  Bollo (phantom BoM) → Flour + Water + Yeast

Usage:
  docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo \
    < addons/test_pos_inventory_deduction.py

Requires: import_initial.py + import_products.py + setup_test_inventory.py
already run (stock must have inventory quantities).
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


def record_baseline(env):
    ProductProduct = env['product.product']
    baseline = {}
    for pp in ProductProduct.search([('is_storable', '=', True)]):
        baseline[pp.id] = {
            'name': pp.display_name,
            'qty': pp.qty_available,
            'uom': pp.uom_id.name,
        }
    return baseline


def diff_stock(env, baseline):
    ProductProduct = env['product.product']
    diffs = {}
    for pp_id, info in baseline.items():
        pp = ProductProduct.browse(pp_id)
        if not pp.exists():
            continue
        after = pp.qty_available
        diff = round(after - info['qty'], 4)
        if abs(diff) > 0.0001:
            diffs[pp_id] = {
                'name': info['name'],
                'before': info['qty'],
                'after': after,
                'diff': diff,
                'uom': info['uom'],
            }
    return diffs


print("=" * 60)
print("  PHANTOM BOM INVENTORY DEDUCTION TEST")
print("=" * 60)

ProductTemplate = env['product.template']
ProductProduct = env['product.product']

# ── 1. Locate stock location ─────────────────────────────
print("\n[1/7] Verifying stock location...")
stock_location = env.ref('stock.stock_location_stock', raise_if_not_found=False)
if not stock_location:
    stock_location = env['stock.location'].search(
        [('usage', '=', 'internal')], limit=1
    )
check("Stock location found", bool(stock_location))
if not stock_location:
    print("\nFATAL: No stock location. Run setup_test_inventory.py first.")
    exit(1)

# ── 2. Check for POS config ─────────────────────────────
print("\n[2/7] Verifying POS config...")
pos_config = env['pos.config'].search([], limit=1)
check("POS config exists", bool(pos_config))
if not pos_config:
    print("\nFATAL: No POS config. Run import_products.py first.")
    exit(1)

# ── 3. Check for open POS session or create one ──────────
print("\n[3/7] Ensuring open POS session...")
session = env['pos.session'].search([
    ('config_id', '=', pos_config.id),
    ('state', '=', 'opened'),
], limit=1)
if not session:
    try:
        session = env['pos.session'].create({'config_id': pos_config.id})
        session.action_pos_session_open()
        print(f"  Created and opened session: {session.name}")
    except Exception as e:
        draft = env['pos.session'].search([
            ('config_id', '=', pos_config.id),
            ('state', '=', 'opening_control'),
        ], limit=1)
        if draft:
            draft.action_pos_session_open()
            session = draft
            print(f"  Opened draft session: {session.name}")
check("POS session open", bool(session))

# ── 4. Baseline inventory ───────────────────────────────
print("\n[4/7] Recording baseline inventory...")
baseline = record_baseline(env)
print(f"  Recorded {len(baseline)} storable products")
check("Baseline recorded", len(baseline) > 0)

# ── 5. Choose test pizza and compute expected deduction ──
print("\n[5/7] Analyzing test pizza BoM chain...")

test_pizza_name = "Mozzarella"
pizza_tmpl = ProductTemplate.search([('name', '=', test_pizza_name)], limit=1)
check(f"Pizza '{test_pizza_name}' exists", bool(pizza_tmpl))

pizza_variant = ProductProduct.search(
    [('product_tmpl_id', '=', pizza_tmpl.id)], limit=1
)
check(f"Pizza variant exists", bool(pizza_variant))

bom = env['mrp.bom'].search([
    ('product_tmpl_id', '=', pizza_tmpl.id),
    ('type', '=', 'phantom'),
], limit=1)
check(f"Phantom BoM exists for {test_pizza_name}", bool(bom))

# Expand BoM to compute expected ingredient deductions
expected_deductions = {}

def expand_bom_line(product_id, qty):
    pt = product_id.product_tmpl_id
    sub_bom = env['mrp.bom'].search([
        ('product_tmpl_id', '=', pt.id),
        ('type', '=', 'phantom'),
    ], limit=1)
    if sub_bom:
        for line in sub_bom.bom_line_ids:
            expand_bom_line(line.product_id, line.product_qty * qty)
    else:
        name = product_id.display_name
        ptmpl_id = product_id.product_tmpl_id.id
        if ptmpl_id in expected_deductions:
            expected_deductions[ptmpl_id]['qty'] = round(
                expected_deductions[ptmpl_id]['qty'] + qty, 4
            )
        else:
            expected_deductions[ptmpl_id] = {
                'name': name,
                'qty': round(qty, 4),
                'uom': product_id.uom_id.name,
            }

for line in bom.bom_line_ids:
    expand_bom_line(line.product_id, line.product_qty)

qty_to_sell = 2
print(f"\n  Selling {qty_to_sell}x {test_pizza_name}")
print(f"  Expected deductions:")
for pid, info in expected_deductions.items():
    total_qty = round(info['qty'] * qty_to_sell, 4)
    print(f"    - {info['name']}: -{total_qty} {info['uom']}")

check("Expected deductions computed", len(expected_deductions) > 0)

# ── 6. Create POS order ─────────────────────────────────
print("\n[6/7] Creating POS order and processing...")

partner = env.ref('base.partner_admin', raise_if_not_found=False)
if not partner:
    partner = env['res.partner'].search([('customer_rank', '>', 0)], limit=1)
if not partner:
    partner = env['res.partner'].create({
        'name': 'Test Customer',
        'customer_rank': 1,
    })

# Get a cash payment method
payment_method = env['pos.payment.method'].search([
    ('is_cash_count', '=', True),
], limit=1)
if not payment_method:
    payment_method = env['pos.payment.method'].search([], limit=1)
check("Payment method found", bool(payment_method))

pos_order_created = False
pos_order_name = None
try:
    order = env['pos.order'].create({
        'session_id': session.id,
        'partner_id': partner.id,
        'pricelist_id': pos_config.pricelist_id.id or env['product.pricelist'].search([], limit=1).id,
        'lines': [(0, 0, {
            'product_id': pizza_variant.id,
            'qty': qty_to_sell,
            'price_unit': pizza_tmpl.list_price or 0,
        })],
        'statement_ids': [(0, 0, {
            'amount': (pizza_tmpl.list_price or 0) * qty_to_sell,
            'payment_method_id': payment_method.id,
            'name': 'Test payment',
        })],
    })
    order.action_pos_order_done()
    pos_order_created = True
    pos_order_name = order.name
    print(f"  POS order: {order.name}")
    print(f"  Amount: {order.amount_total}")
    check("POS order created and processed", True)
except Exception as e:
    check("POS order created and processed", False, str(e))
    print("\n  Trying Sale Order fallback...")
    try:
        so = env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': pizza_variant.id,
                'product_uom_qty': qty_to_sell,
                'price_unit': pizza_tmpl.list_price or 0,
            })],
        })
        so.action_confirm()
        print(f"  Sale Order: {so.name}")
        picking = so.picking_ids[:1] if so.picking_ids else None
        if picking:
            picking.action_assign()
            for move in picking.move_ids:
                move.write({'quantity': move.product_uom_qty})
            picking._action_done()
            print(f"  Picking validated — stock deducted!")
            pos_order_name = so.name
        else:
            print("  WARNING: No delivery picking created.")
            ERRORS.append("No delivery picking for Sale Order")
    except Exception as e2:
        print(f"  Sale Order also failed: {e2}")
        ERRORS.append(f"Both POS and Sale Order failed")

# ── 7. Compare stock ─────────────────────────────────────
print(f"\n[7/7] Stock comparison (after selling {qty_to_sell}x {test_pizza_name}):")
print("  " + "-" * 75)
print(f"  {'Product':40s} {'Before':>8s} {'After':>8s} {'Diff':>8s}  {'Expected':>8s}  Status")
print("  " + "-" * 75)

diffs = diff_stock(env, baseline)
all_verified = True

# Check each expected deduction
for ptmpl_id, exp in expected_deductions.items():
    product = ProductProduct.search([
        ('product_tmpl_id', '=', ptmpl_id),
    ], limit=1)
    before_info = baseline.get(product.id, {})
    before = before_info.get('qty', 0)
    after = product.qty_available
    actual_diff = round(after - before, 4)
    exp_qty = round(-exp['qty'] * qty_to_sell, 4)
    match = abs(actual_diff - exp_qty) < 0.01
    status = "OK" if match else "MISMATCH"
    if not match:
        all_verified = False
    name = exp['name'][:40]
    print(f"  {name:40s} {before:8.3f} {after:8.3f} {actual_diff:8.3f}  {exp_qty:8.3f}  {status}")
    check(
        f"Ingredient '{exp['name']}' deduction",
        match,
        f"got {actual_diff}, expected {exp_qty}"
    )

# Check for unexpected changes
for pp_id, d in diffs.items():
    if d['name'] not in [e['name'] for e in expected_deductions.values()]:
        print(f"  ! UNEXPECTED CHANGE: {d['name']:40s} -> {d['diff']:+.3f}")
        all_verified = False

print("  " + "-" * 75)

# ── Summary ──────────────────────────────────────────────
print()
print("=" * 60)
print("  TEST RESULTS")
print("=" * 60)
print(f"  Passed: {PASS}")
print(f"  Failed: {FAIL}")
if ERRORS:
    print()
    print("  Errors:")
    for e in ERRORS:
        print(f"    - {e}")

print()
if FAIL == 0 and all_verified:
    print("  ✓ ALL TESTS PASSED")
    print(f"  Phantom BoM deduction verified for {qty_to_sell}x {test_pizza_name}")
    print()
    print("  Chain: Pizza → Bollo de Masa → Harina + Agua + Levadura")
    print("       + Toppings (Muzzarella, Salsa, Aceitunas)")
    print()
    print("  The phantom/kit BoM system correctly expands:")
    print("  1. Pizza BoM → Bollo + ingredients")
    print("  2. Bollo BoM  → Flour + Water + Yeast")
    print("  3. All raw ingredients deducted from stock")
elif FAIL > 0:
    print(f"  ✗ {FAIL} TEST(S) FAILED")
    print("  Check the Mismatch lines above for details.")
else:
    print(f"  ✗ Tests incomplete — see errors above.")

print(f"\n  POS order: {pos_order_name or 'N/A'}")
print()
print("=" * 60)

env.cr.rollback()
