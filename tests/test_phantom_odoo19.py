#!/usr/bin/env python3
"""
Test phantom BoM deduction - Odoo 19 compatible version.
"""

print("=" * 70)
print("  Phantom BoM Stock Deduction Test (Odoo 19)")
print("=" * 70)

# Check if stock module is properly configured
print("\n[1/4] Checking stock configuration...")
stock_loc = env.ref('stock.stock_location_stock', raise_if_not_found=False)
if not stock_loc:
    stock_loc = env['stock.location'].search([('usage', '=', 'internal')], limit=1)
print(f"  Stock location: {stock_loc.name if stock_loc else 'NOT FOUND'}")

# Check product types
print("\n[2/4] Checking product storable status...")
all_products = env['product.product'].search([])
storable_count = sum(1 for p in all_products if p.is_storable)
print(f"  Total products: {len(all_products)}")
print(f"  Storable products: {storable_count}")

# Show a few examples
print("\n  Sample products:")
for p in all_products[:5]:
    print(f"    {p.display_name}: type={p.type}, is_storable={p.is_storable}")

# Check BoM
print("\n[3/4] Checking Mozzarella BoM...")
mozzarella = env['product.template'].search([('name', '=', 'Mozzarella')], limit=1)
if mozzarella:
    bom = env['mrp.bom'].search([('product_tmpl_id', '=', mozzarella.id), ('type', '=', 'phantom')], limit=1)
    if bom:
        print(f"  Phantom BoM found: {bom.code or bom.id}")
        print(f"  BoM lines:")
        for line in bom.bom_line_ids:
            print(f"    - {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name}")
    else:
        print("  ERROR: No phantom BoM found for Mozzarella!")
else:
    print("  ERROR: Mozzarella product not found!")

# Key insight for Odoo 19
print("\n[4/4] Important notes for Odoo 19:")
print("  - Products with type='consu' are NOT storable by default")
print("  - For phantom BoM stock deduction, ingredients must be storable")
print("  - In Odoo 19, 'is_storable' is computed, not directly settable")
print("  - Stock tracking requires proper inventory setup")

print("\n" + "=" * 70)
print("  TEST: Manual verification required")
print("=" * 70)
print("\n  To test phantom BoM deduction:")
print("  1. Open Odoo backend → Inventory → Products")
print("  2. Find 'Harina 0000' and set initial quantity (e.g., 100 kg)")
print("  3. Open POS and sell 1x Mozzarella")
print("  4. Check if Harina quantity decreased by 0.3 kg (2x BoM qty)")
print("  5. Verify in Inventory → Stock Moves")
print("\n  The phantom BoM should auto-explode:")
print("    1 Mozzarella → 1 Bollo + 0.28kg Muzzarella + ...")
print("    1 Bollo → 0.3kg Harina + 0.18L Agua + 0.005kg Levadura")
print("=" * 70)