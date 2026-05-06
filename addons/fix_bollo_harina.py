#!/usr/bin/env python3
print("=" * 70)
print("  Fixing Bollo de Masa BoM - Adding missing Harina")
print("=" * 70)

bollo = env['product.template'].search([('name', '=', 'Bollo de Masa (Pre-pizza)')], limit=1)
harina = env['product.template'].search([('name', '=', 'Harina 0000')], limit=1)

if not bollo or not harina:
    print("ERROR: Bollo or Harina not found!")
    exit(1)

print(f"Bollo: {bollo.name} (ID: {bollo.id})")
print(f"Harina: {harina.name} (ID: {harina.id})")

bom = env['mrp.bom'].search([('product_tmpl_id', '=', bollo.id), ('type', '=', 'phantom')], limit=1)
if not bom:
    print("ERROR: No phantom BoM for Bollo!")
    exit(1)

print(f"\nCurrent BoM lines ({len(bom.bom_line_ids)}):")
for line in bom.bom_line_ids:
    print(f"  - {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name}")

# Check if Harina is already in the BoM
harina_in_bom = any(line.product_id.product_tmpl_id.id == harina.id for line in bom.bom_line_ids)
if harina_in_bom:
    print("\nHarina is already in the BoM!")
else:
    # Add Harina to the BoM
    harina_variant = env['product.product'].search([('product_tmpl_id', '=', harina.id)], limit=1)
    env['mrp.bom.line'].create({
        'bom_id': bom.id,
        'product_id': harina_variant.id,
        'product_qty': 0.3,
        'product_uom_id': harina_variant.uom_id.id,
    })
    env.cr.commit()
    print(f"\n✓ Added Harina 0000: 0.3 kg to Bollo BoM")

# Verify
bom.refresh()
print(f"\nUpdated BoM lines ({len(bom.bom_line_ids)}):")
for line in bom.bom_line_ids:
    print(f"  - {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name}")

print("=" * 70)