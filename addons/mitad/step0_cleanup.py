#!/usr/bin/env python3
print("=" * 70)
print("  Step 0: Full Cleanup")
print("=" * 70)

# CRITICAL: Delete ALL attribute lines first (to clear foreign keys)
print("\n  [1/4] Removing ALL attribute lines...")
AttributeLine = env['product.template.attribute.line']
all_lines = AttributeLine.search([])
if all_lines:
    print(f"    Deleting {len(all_lines)} attribute lines...")
    all_lines.unlink()
    env.cr.commit()
    print(f"    ✓ Deleted all attribute lines")

# Now delete attributes
print("\n  [2/4] Removing Lado A and Lado B attributes...")
ProductAttribute = env['product.attribute']
for attr_name in ['Lado A', 'Lado B']:
    attr = ProductAttribute.search([('name', '=', attr_name)], limit=1)
    if attr:
        attr.unlink()
        print(f"    ✓ Removed: {attr_name}")
env.cr.commit()

# Remove BoM
print("\n  [3/4] Removing Mitad y Mitad BoM...")
ProductTemplate = env['product.template']
MrpBom = env['mrp.bom']
mitad = ProductTemplate.search([('name', '=', '🍕 Mitad y Mitad')], limit=1)
if mitad:
    boms = MrpBom.search([('product_tmpl_id', '=', mitad.id)])
    for b in boms:
        print(f"    ✓ Removed BoM: {b.code or b.id}")
        b.unlink()
    env.cr.commit()

# Remove server actions
print("\n  [4/4] Removing server actions...")
ServerAction = env['ir.actions.server']
BaseAutomation = env['base.automation']
for name in ['Mitad y Mitad - MAX Pricing', 'Mitad y Mitad - Stock Deduction']:
    for a in ServerAction.search([('name', '=', name)]):
        a.unlink()
        print(f"    ✓ Removed: {name}")

for name in ['Mitad y Mitad - Price on Create', 'Mitad y Mitad - Price on Write', 'Mitad y Mitad - Stock on Paid']:
    for a in BaseAutomation.search([('name', '=', name)]):
        a.unlink()
        print(f"    ✓ Removed: {name}")

env.cr.commit()

# Reset product
if mitad:
    mitad.write({'list_price': 12000})
    env.cr.commit()
    print(f"\n  Reset 🍕 Mitad y Mitad price to 12000")

print("\n  ✓ Cleanup complete!")
print("=" * 70)