#!/usr/bin/env python3
"""
Remove attributes from Mitad y Mitad to make it a simple product.
Run this if you want to disable the half-pizza configurator.
"""

print("=" * 70)
print("  Removing Mitad y Mitad Attributes")
print("=" * 70)

mitad = env['product.template'].search([('name', '=', '🍕 Mitad y Mitad')], limit=1)

if not mitad:
    print("  Mitad y Mitad not found!")
    exit(1)

print(f"\n  Found: {mitad.name}")

# Check for attribute lines
AttributeLine = env['product.template.attribute.line']
lines = AttributeLine.search([('product_tmpl_id', '=', mitad.id)])

if lines:
    print(f"  Found {len(lines)} attribute line(s):")
    for l in lines:
        attr_name = l.attribute_id.name if l.attribute_id else 'Unknown'
        print(f"    - {attr_name}")
    
    lines.unlink()
    env.cr.commit()
    print(f"\n  ✓ Removed {len(lines)} attribute lines")
else:
    print("  No attribute lines found")

# Check for BoM
MrpBom = env['mrp.bom']
boms = MrpBom.search([('product_tmpl_id', '=', mitad.id)])
if boms:
    for b in boms:
        b.unlink()
        print(f"  ✓ Removed BoM: {b.code or b.id}")
    env.cr.commit()

# Reset to simple product
mitad.write({'list_price': 12000})
env.cr.commit()
print(f"\n  ✓ Reset to simple product (price: 12000)")
print("\n  Now Mitad y Mitad will behave like a regular product")
print("=" * 70)