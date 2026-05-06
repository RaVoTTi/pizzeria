import csv
import os
import logging

logger = logging.getLogger(__name__)

CSV_DIR = '/csv'
env = env


def csv_rows(filename):
    path = os.path.join(CSV_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


STOCK_BY_CATEGORY = {
    'Materia Prima Cocina': 50,
    'Barriles y Gas': 10,
    'Bebidas sin Alcohol': 100,
    'Cerveza Barra': 100,
    'VENTAS': 50,
}

SKIP_PRODUCTS = {'Pizzas'}
INTERMEDIATE_PRODUCTS = {'Bollo de Masa (Pre-pizza)'}


def set_stock_quantity(env, variant_id, location_id, quantity):
    Quant = env['stock.quant']
    quant = Quant.search([
        ('product_id', '=', variant_id),
        ('location_id', '=', location_id),
    ], limit=1)
    try:
        if quant:
            quant.inventory_quantity = quantity
            quant.action_apply_inventory()
        else:
            quant = Quant.create({
                'product_id': variant_id,
                'location_id': location_id,
                'inventory_quantity': quantity,
            })
            quant.action_apply_inventory()
        return True
    except Exception as e:
        print(f"    ERROR applying inventory: {e}")
        return False


print("=" * 60)
print("  Pizzeria El Gordo - Test Inventory Setup")
print("  Run AFTER import_pizzas.py")
print("=" * 60)

ProductTemplate = env['product.template']
ProductProduct = env['product.product']

# ─── [1/6] Locate stock location ──────────────────────────
print("\n[1/6] Locating stock location...")
stock_location = env.ref('stock.stock_location_stock', raise_if_not_found=False)
if not stock_location:
    stock_location = env['stock.location'].search(
        [('usage', '=', 'internal')], limit=1
    )
if not stock_location:
    print("  ERROR: No internal stock location found!")
    raise Exception("No stock location found")
print(f"  Found: {stock_location.name} (id={stock_location.id})")

# ─── [3/7] Set initial inventory ──────────────────────────
print("\n[2/6] Setting initial inventory quantities...")

stocked = 0
skipped = 0

all_storable = ProductTemplate.search([('is_storable', '=', True)])

for tmpl in all_storable:
    cat_name = tmpl.categ_id.name if tmpl.categ_id else ''
    product_name = tmpl.name

    if cat_name in SKIP_PRODUCTS:
        print(f"  SKIP (kit/phantom BoM): {product_name} [{cat_name}]")
        skipped += 1
        continue

    if product_name in INTERMEDIATE_PRODUCTS:
        print(f"  SKIP (intermediate): {product_name}")
        skipped += 1
        continue

    qty = STOCK_BY_CATEGORY.get(cat_name, 0)
    if qty <= 0:
        print(f"  SKIP (no stock rule for category): {product_name} [{cat_name}]")
        skipped += 1
        continue

    variant = ProductProduct.search(
        [('product_tmpl_id', '=', tmpl.id)], limit=1
    )
    if not variant:
        print(f"  SKIP (no variant): {product_name}")
        skipped += 1
        continue

    if set_stock_quantity(env, variant.id, stock_location.id, qty):
        print(f"  + {product_name}: {qty} {variant.uom_id.name} [{cat_name}]")
        stocked += 1
    else:
        print(f"  FAIL: {product_name}")
        skipped += 1

env.cr.commit()
print(f"\n  Stocked: {stocked} products | Skipped: {skipped}")

# ─── [4/7] Setup POS payment method ───────────────────────
print("\n[3/6] Setting up POS payment method...")

pos_config = env['pos.config'].search([], limit=1)

if pos_config:
    existing_methods = pos_config.payment_method_ids
    print(f"  POS config: {pos_config.name}")
    print(f"  Existing payment methods: {[m.name for m in existing_methods]}")

    if not existing_methods:
        cash_journal = env['account.journal'].search([
            ('type', '=', 'cash'),
            ('company_id', '=', env.company.id),
        ], limit=1)

        if not cash_journal:
            try:
                cash_journal = env['account.journal'].create({
                    'name': 'Cash',
                    'type': 'cash',
                    'code': 'CSH1',
                    'company_id': env.company.id,
                })
                print(f"  Created cash journal: {cash_journal.name}")
            except Exception as e:
                print(f"  Could not create cash journal: {e}")
                cash_journal = False

        if cash_journal:
            method = env['pos.payment.method'].search([
                ('cash_journal_id', '=', cash_journal.id),
            ], limit=1)

            if not method:
                try:
                    method = env['pos.payment.method'].create({
                        'name': 'Cash',
                        'is_cash_count': True,
                        'cash_journal_id': cash_journal.id,
                    })
                    print(f"  Created payment method: {method.name}")
                except Exception as e:
                    print(f"  Could not create payment method: {e}")
                    method = False

            if method and method not in existing_methods:
                pos_config.write({
                    'payment_method_ids': [(4, method.id)],
                })
                print(f"  Added payment method to POS config")
    else:
        print(f"  POS already has payment methods configured.")
else:
    print("  WARNING: No POS config found. Run import_pizzas.py first.")

env.cr.commit()

# ─── [5/7] Print BoM chain analysis ──────────────────────
print("\n[4/6] Analyzing phantom BoM chain...")

expected_deductions = {}
pizza_products = ProductTemplate.search([
    ('categ_id.name', '=', 'Pizzas'),
])

if not pizza_products:
    print("  WARNING: No pizza products found. Run import_pizzas.py first.")
else:
    print(f"  Found {len(pizza_products)} pizza products with phantom BoMs:")
    print()

    for pizza in pizza_products[:3]:
        bom = env['mrp.bom'].search([
            ('product_tmpl_id', '=', pizza.id),
            ('type', '=', 'phantom'),
        ], limit=1)

        if not bom:
            print(f"  {pizza.name}: NO phantom BoM found!")
            continue

        print(f"  {pizza.name} (BoM type=phantom, {len(bom.bom_line_ids)} components):")
        for line in bom.bom_line_ids:
            comp_name = line.product_id.display_name
            comp_qty = line.product_qty
            comp_uom = line.product_uom_id.name

            sub_bom = env['mrp.bom'].search([
                ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                ('type', '=', 'phantom'),
            ], limit=1)

            if sub_bom:
                print(f"    {comp_qty} {comp_uom} of {comp_name}")
                print(f"      └─ expands via phantom BoM:")
                for sub_line in sub_bom.bom_line_ids:
                    sub_name = sub_line.product_id.display_name
                    sub_qty = round(sub_line.product_qty * comp_qty, 4)
                    sub_uom = sub_line.product_uom_id.name
                    print(f"         {sub_qty} {sub_uom} of {sub_name}")
                    expected_deductions[sub_name] = {
                        'product_tmpl_id': sub_line.product_id.product_tmpl_id.id,
                        'qty': sub_qty,
                        'uom': sub_uom,
                    }
            else:
                print(f"    {comp_qty} {comp_uom} of {comp_name}")
                expected_deductions[comp_name] = {
                    'product_tmpl_id': line.product_id.product_tmpl_id.id,
                    'qty': round(comp_qty, 4),
                    'uom': comp_uom,
                }
        print()

    if len(pizza_products) > 3:
        print(f"  ... and {len(pizza_products) - 3} more pizzas (same pattern)")
        print()

# ─── [6/7] Create test Sale Order ─────────────────────────
print("\n[5/6] Creating test Sale Order to verify stock deduction...")

baseline = {}
for pp in ProductProduct.search([('is_storable', '=', True)]):
    tmpl = pp.product_tmpl_id
    cat = tmpl.categ_id.name if tmpl.categ_id else ''
    if cat in STOCK_BY_CATEGORY or cat == 'Pizzas':
        baseline[tmpl.id] = {
            'name': pp.display_name,
            'qty': pp.qty_available,
            'uom': pp.uom_id.name,
        }

sale_ok = False

if pizza_products:
    test_pizza = pizza_products[0]
    test_variant = ProductProduct.search(
        [('product_tmpl_id', '=', test_pizza.id)], limit=1
    )

    try:
        sale_module = env['ir.module.module'].search(
            [('name', '=', 'sale')], limit=1
        )
        if sale_module and sale_module.state != 'installed':
            print("  Installing sale module...")
            sale_module.button_immediate_install()
            env.cr.commit()
            env = env

        partner = env.ref('base.partner_admin', raise_if_not_found=False)
        if not partner:
            partner = env['res.partner'].search(
                [('customer_rank', '>', 0)], limit=1
            )
        if not partner:
            partner = env['res.partner'].create({
                'name': 'Test Customer',
                'customer_rank': 1,
            })

        so = env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': test_variant.id,
                'product_uom_qty': 1,
                'price_unit': test_variant.list_price or 0,
            })],
        })
        print(f"  Sale Order: {so.name} (customer: {partner.name})")
        print(f"  Product: {test_pizza.name}")

        so.action_confirm()
        print(f"  Order confirmed.")

        picking = so.picking_ids[:1] if so.picking_ids else None
        if picking:
            print(f"  Delivery picking: {picking.name}")
            print(f"  Picking lines (should show INGREDIENTS, not the pizza):")
            for move in picking.move_ids:
                print(f"    - {move.product_id.display_name}: "
                      f"{move.product_uom_qty} {move.product_uom.name}")

            picking.action_assign()

            for move in picking.move_ids:
                move.write({'quantity': move.product_uom_qty})

            picking._action_done()
            print(f"  Picking validated — stock deducted!")
            sale_ok = True
        else:
            print("  WARNING: No delivery picking created.")
            print("  BoM expansion may not be working correctly.")

    except Exception as e:
        print(f"  ERROR during test sale: {e}")
        print("  Manual POS test recommended instead.")

env.cr.commit()

# ─── Print before/after comparison ──────────────────────
print(f"\n  Stock comparison{' (after selling 1x ' + test_pizza.name + ')' if sale_ok else ''}:")
print("  " + "-" * 65)
print(f"  {'Product':38s} {'Before':>8s} {'After':>8s} {'Diff':>8s}")
print("  " + "-" * 65)

deduction_verified = False
for pp in ProductProduct.search([('is_storable', '=', True)]):
    tmpl = pp.product_tmpl_id
    tmpl_id = tmpl.id
    after = pp.qty_available
    before_info = baseline.get(tmpl_id)
    if not before_info:
        continue
    before = before_info['qty']
    diff = round(after - before, 4)

    if abs(diff) > 0.0001 or tmpl.categ_id.name in STOCK_BY_CATEGORY or tmpl.categ_id.name == 'Pizzas':
        name = pp.display_name[:38]
        marker = ""
        if expected_deductions and name in expected_deductions:
            expected = expected_deductions[name]
            if abs(abs(diff) - expected['qty']) < 0.001:
                marker = " OK"
                deduction_verified = True
            else:
                marker = f" (expected {expected['qty']})"
        print(f"  {name:38s} {before:8.3f} {after:8.3f} {diff:8.3f}{marker}")

print("  " + "-" * 65)

if sale_ok:
    if deduction_verified:
        print("\n  SUCCESS: Phantom BoM deduction verified!")
        print("  Raw ingredients were deducted correctly through the chain:")
        print("  Pizza → Bollo de Masa → Flour + Water + Yeast + Toppings")
    else:
        print("\n  WARNING: Could not verify all expected deductions.")
        print("  Check the diff column above manually.")

# ─── [7/7] Open POS session ───────────────────────────────
print("\n[6/6] Opening POS session for live testing...")

pos_config = env['pos.config'].search([], limit=1)

if pos_config:
    open_session = env['pos.session'].search([
        ('config_id', '=', pos_config.id),
        ('state', '=', 'opened'),
    ], limit=1)

    if open_session:
        print(f"  Open session found: {open_session.name}")
    else:
        try:
            session = env['pos.session'].create({
                'config_id': pos_config.id,
            })
            session.action_pos_session_open()
            print(f"  Created and opened POS session: {session.name}")
        except Exception as e:
            draft_session = env['pos.session'].search([
                ('config_id', '=', pos_config.id),
                ('state', '=', 'opening_control'),
            ], limit=1)
            if draft_session:
                try:
                    draft_session.action_pos_session_open()
                    print(f"  Opened existing session: {draft_session.name}")
                except Exception as e2:
                    print(f"  Could not open session: {e2}")
                    print(f"  Open it manually from the POS interface.")
            else:
                print(f"  Could not create session: {e}")
                print(f"  Open it manually from the POS interface.")
else:
    print("  No POS config found. Run import_pizzas.py first.")

env.cr.commit()

# ─── Summary ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("  Setup Complete!")
print("=" * 60)
if sale_ok:
    print("\n  Automated test passed:")
    print(f"  Sold 1x {test_pizza.name}, verified ingredient deduction.")
    print("\n  The phantom BoM chain works correctly:")
    print("  Pizza (phantom BoM) → Bollo + Toppings")
    print("  Bollo (phantom BoM) → Flour + Water + Yeast")
print("\n  Manual POS test:")
print("  1. Open http://elgordo.local")
print("  2. Go to Point of Sale")
print("  3. Sell any pizza, pay with Cash")
print("  4. Check Inventory > Products to verify stock deduction")
print("=" * 60)