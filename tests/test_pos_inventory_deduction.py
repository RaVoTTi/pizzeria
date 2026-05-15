"""
Phantom BoM Inventory Deduction Test — Odoo 19

Verifies that the two-level phantom BoM chain is correctly configured
and that stock moves are created when products are sold.

  Pizza (phantom) → Bollo de Masa + Toppings
  Bollo (phantom) → Flour + Water + Yeast

This is the CORE feature of the pizzeria system. If the BoM chain is
broken, inventory tracking won't work.

Usage:
  docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo \
    < tests/test_pos_inventory_deduction.py

IMPORTANT: In Odoo Community, POS stock moves are only created when the
POS session is closed and validated. This test verifies:
1. BoM chain configuration (immediate)
2. Stock deduction via Sale Order (immediate, proves BoM logic)
3. POS order creation and payment (workflow test)

For POS stock deduction verification, close the session manually in the UI
or use the Sale Order test which proves the BoM chain works correctly.
"""

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


def expand_bom_chain(env, bom, qty_multiplier=1.0):
    """Recursively expand a phantom BoM to get leaf ingredient products."""
    ingredients = {}

    def _expand(bom_obj, mult):
        for line in bom_obj.bom_line_ids:
            sub_bom = env['mrp.bom'].search([
                ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                ('type', '=', 'phantom'),
            ], limit=1)
            if sub_bom:
                _expand(sub_bom, line.product_qty * mult)
            else:
                ptmpl_id = line.product_id.product_tmpl_id.id
                ingredients[ptmpl_id] = {
                    'name': line.product_id.display_name,
                    'uom': line.product_id.uom_id.name,
                    'qty': round(line.product_qty * mult, 4),
                }

    _expand(bom, qty_multiplier)
    return ingredients


def get_stock_levels(env, ingredient_names):
    """Record current stock levels for given ingredients."""
    ProductTemplate = env['product.template']
    ProductProduct = env['product.product']
    levels = {}
    for name in ingredient_names:
        tmpl = ProductTemplate.search([('name', '=', name)], limit=1)
        if tmpl:
            variant = ProductProduct.search([('product_tmpl_id', '=', tmpl.id)], limit=1)
            levels[name] = variant.qty_available if variant else 0
    return levels


def verify_stock_deduction(env, baseline, expected_ingredients, ingredient_names):
    """Verify that stock was deducted correctly."""
    ProductTemplate = env['product.template']
    ProductProduct = env['product.product']
    all_ok = True
    for name in ingredient_names:
        tmpl = ProductTemplate.search([('name', '=', name)], limit=1)
        if tmpl:
            variant = ProductProduct.search([('product_tmpl_id', '=', tmpl.id)], limit=1)
            after = variant.qty_available
            diff = round(after - baseline[name], 4)
            expected = round(-expected_ingredients.get(tmpl.id, {}).get('qty', 0), 4)
            match = abs(diff - expected) < 0.01
            status = "OK" if match else "MISMATCH"
            if not match:
                all_ok = False
            print(f"    {name}: {baseline[name]} → {after} (diff: {diff}, expected: {expected}) {status}")
    return all_ok


print("=" * 70)
print("  PHANTOM BOM INVENTORY DEDUCTION TEST (Odoo 19)")
print("=" * 70)

ProductTemplate = env['product.template']
ProductProduct = env['product.product']

# ── 1. Verify BoM chain exists ───────────────────────────
print("\n[1/6] Verifying phantom BoM chain...")

test_pizza_name = "Mozzarella"
pizza_tmpl = ProductTemplate.search([('name', '=', test_pizza_name)], limit=1)
check(f"Pizza '{test_pizza_name}' exists", bool(pizza_tmpl))

pizza_variant = ProductProduct.search(
    [('product_tmpl_id', '=', pizza_tmpl.id)], limit=1
)
check("Pizza variant exists", bool(pizza_variant))

bom = env['mrp.bom'].search([
    ('product_tmpl_id', '=', pizza_tmpl.id),
    ('type', '=', 'phantom'),
], limit=1)
check(f"Phantom BoM exists for {test_pizza_name}", bool(bom))

# ── 2. Verify Bollo de Masa intermediate BoM ─────────────
print("\n[2/6] Verifying Bollo de Masa intermediate BoM...")

bollo_tmpl = ProductTemplate.search(
    [('name', '=', 'Bollo de Masa (Pre-pizza)')], limit=1
)
check("Bollo de Masa product exists", bool(bollo_tmpl))

bollo_bom = env['mrp.bom'].search([
    ('product_tmpl_id', '=', bollo_tmpl.id),
    ('type', '=', 'phantom'),
], limit=1) if bollo_tmpl else None
check("Bollo de Masa has phantom BoM", bool(bollo_bom))

if bollo_bom:
    bollo_ingredients = [line.product_id.display_name for line in bollo_bom.bom_line_ids]
    print(f"    Bollo ingredients: {', '.join(bollo_ingredients)}")
    check("Bollo has Harina (flour)", any('Harina' in i for i in bollo_ingredients))
    check("Bollo has Agua (water)", any('Agua' in i for i in bollo_ingredients))
    check("Bollo has Levadura (yeast)", any('Levadura' in i for i in bollo_ingredients))

# ── 3. Verify ingredients are storable ───────────────────
print("\n[3/6] Verifying ingredients are storable...")

expected_ingredient_names = ['Harina 0000', 'Agua Filtrada', 'Levadura Fresca',
                              'Muzzarella Cilindro', 'Salsa de Tomate Base', 'Aceitunas Verdes']
for name in expected_ingredient_names:
    tmpl = ProductTemplate.search([('name', '=', name)], limit=1)
    if tmpl:
        variant = ProductProduct.search([('product_tmpl_id', '=', tmpl.id)], limit=1)
        is_storable = variant.is_storable if variant else False
        check(f"{name} is storable", is_storable, f"type={variant.type if variant else 'N/A'}")
    else:
        check(f"{name} exists", False, "Product not found")

# ── 4. Compute expected ingredient products ──────────────
print("\n[4/6] Computing expected ingredient products...")

qty_to_sell = 2
expected_ingredients = {}
if bom:
    expected_ingredients = expand_bom_chain(env, bom, qty_to_sell)

print(f"\n  Expected ingredient products for {qty_to_sell}x {test_pizza_name}:")
for pid, info in sorted(expected_ingredients.items(), key=lambda x: x[1]['name']):
    print(f"    - {info['name']}: {info['qty']} {info['uom']}")

check("Expected ingredients computed", len(expected_ingredients) > 0)

# ── 5. Test stock deduction via Sale Order ───────────────
print("\n[5/6] Testing stock deduction via Sale Order...")

baseline_so = get_stock_levels(env, expected_ingredient_names)
print(f"  Baseline stock levels:")
for name, qty in sorted(baseline_so.items()):
    print(f"    {name}: {qty}")

partner = env["res.partner"].search([], limit=1)
if not partner:
    partner = env["res.partner"].create({"name": "Test Customer"})

try:
    so = env['sale.order'].create({
        'partner_id': partner.id,
        'order_line': [(0, 0, {
            'product_id': pizza_variant.id,
            'product_uom_qty': qty_to_sell,
            'price_unit': pizza_tmpl.list_price or 10.0,
        })],
    })
    check("Sale Order created", bool(so))
    print(f"  Sale Order: {so.name}")

    so.action_confirm()
    check("Sale Order confirmed", so.state == 'sale')

    picking = so.picking_ids[:1] if so.picking_ids else None
    if picking:
        check("Delivery picking exists", True)
        print(f"  Picking: {picking.name}")

        picking_products = [m.product_id.display_name for m in picking.move_ids]
        print(f"  Picking products: {', '.join(picking_products[:5])}...")

        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.button_validate()
        check("Picking validated", picking.state == 'done')

        print(f"\n  Stock changes after selling {qty_to_sell}x {test_pizza_name}:")
        so_ok = verify_stock_deduction(env, baseline_so, expected_ingredients, expected_ingredient_names)
        check("Stock deducted correctly (Sale Order)", so_ok)
    else:
        check("Delivery picking exists", False, "No picking created for Sale Order")

except Exception as e:
    check("Sale Order stock deduction", False, str(e))
    import traceback
    traceback.print_exc()

# ── 6. Verify POS order creation and payment ─────────────
print("\n[6/6] Testing POS order creation and payment...")

pos_config = env['pos.config'].search([], limit=1)
check("POS config exists", bool(pos_config))

if pos_config:
    company = env.ref("base.main_company", raise_if_not_found=False)
    if not company:
        company = env["res.company"].search([], limit=1)

    try:
        # Find or create a POS session
        session = env['pos.session'].search([
            ('config_id', '=', pos_config.id),
            ('state', 'not in', ['closed']),
        ], limit=1)

        if not session:
            session = env["pos.session"].create({
                "config_id": pos_config.id,
            })
            print(f"  Created session: {session.name} (state: {session.state})")
        else:
            print(f"  Using existing session: {session.name} (state: {session.state})")

        # Create POS order
        price = pizza_tmpl.list_price or 10.0
        total = qty_to_sell * price
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
                "product_id": pizza_variant.id,
                "qty": qty_to_sell,
                "price_unit": price,
                "price_subtotal": total,
                "price_subtotal_incl": total,
                "full_product_name": pizza_variant.display_name,
            })],
        })
        check("POS order created", bool(order))
        print(f"  Order: {order.name}")

        # Pay the order
        order.action_pos_order_paid()
        check("Order paid", order.state in ('done', 'paid'))
        print(f"  Order state: {order.state}")

        # NOTE: In Odoo Community, stock moves are only created when the
        # POS session is closed and validated. This is by design to keep
        # POS fast during rush hours. The Sale Order test above proves
        # the BoM chain works correctly.
        print(f"\n  NOTE: POS stock moves are created when session is closed.")
        print(f"  To verify stock deduction, close the session in the UI.")

    except Exception as e:
        check("POS order creation", False, str(e))
        import traceback
        traceback.print_exc()

# ── Summary ──────────────────────────────────────────────
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
    print("  ✓ ALL TESTS PASSED")
    print()
    print("  Phantom BoM stock deduction is working:")
    print("  1. Pizza BoM → Bollo de Masa + Toppings")
    print("  2. Bollo BoM  → Flour + Water + Yeast")
    print("  3. Stock correctly deducted via Sale Order")
    print("  4. POS orders can be created and paid")
    print()
    print("  When a pizza is sold, Odoo automatically:")
    print("  - Explodes the phantom BoM chain")
    print("  - Creates stock moves for each leaf ingredient")
    print("  - Deducts stock without manual manufacturing orders")
    print()
    print("  NOTE: In Odoo Community, POS stock moves are created")
    print("  when the session is closed, not immediately after payment.")
elif FAIL > 0:
    print(f"  ✗ {FAIL} TEST(S) FAILED")
    print()
    print("  TROUBLESHOOTING:")
    print("  1. Verify ingredients are storable: is_storable=True")
    print("  2. Verify BoM type is 'phantom' (not 'normal')")
    print("  3. Check stock moves in Inventory → Reporting → Stock Moves")
    print("  4. Ensure mrp and stock modules are installed")
    print("  5. Run: scripts/nuclear-reset.sh to rebuild from scratch")

print()
print("=" * 70)

env.cr.rollback()
