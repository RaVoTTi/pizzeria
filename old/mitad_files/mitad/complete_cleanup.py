#!/usr/bin/env python3
"""
Complete cleanup of Mitad y Mitad - removes all variants and attributes.
"""

print("=" * 70)
print("  Complete Mitad y Mitad Cleanup")
print("=" * 70)

mitad = env['product.template'].search([('name', '=', '🍕 Mitad y Mitad')], limit=1)

if not mitad:
    print("  Mitad y Mitad not found. Nothing to clean.")
    print("=" * 70)
    exit(0)

print(f"\n  Found: {mitad.name} (ID: {mitad.id})")

# 1. Remove all product variants except the first one
ProductProduct = env['product.product']
variants = ProductProduct.search([('product_tmpl_id', '=', mitad.id)])
print(f"\n  Found {len(variants)} variants")

if len(variants) > 1:
    # Keep only the first one, delete others
    for v in variants[1:]:
        v.unlink()
    print(f"  ✓ Removed {len(variants)-1} extra variants")
    env.cr.commit()

# 2. Remove all product template attribute values
Ptav = env['product.template.attribute.value']
ptavs = Ptav.search([('product_tmpl_id', '=', mitad.id)])
if ptavs:
    print(f"\n  Found {len(ptavs)} product template attribute values")
    ptavs.unlink()
    print(f"  ✓ Removed all ptavs")
    env.cr.commit()

# 3. Remove attribute lines
AttributeLine = env['product.template.attribute.line']
lines = AttributeLine.search([('product_tmpl_id', '=', mitad.id)])
if lines:
    print(f"\n  Found {len(lines)} attribute lines")
    lines.unlink()
    print(f"  ✓ Removed attribute lines")
    env.cr.commit()

# 4. Remove BoMs
MrpBom = env['mrp.bom']
boms = MrpBom.search([('product_tmpl_id', '=', mitad.id)])
if boms:
    print(f"\n  Found {len(boms)} BoMs")
    for b in boms:
        b.unlink()
    print(f"  ✓ Removed BoMs")
    env.cr.commit()

# 5. Reset product
mitad.write({'list_price': 12000})
env.cr.commit()

# Verify
mitad = env['product.template'].browse(mitad.id)
variants_after = ProductProduct.search([('product_tmpl_id', '=', mitad.id)])
ptavs_after = Ptav.search([('product_tmpl_id', '=', mitad.id)])
lines_after = AttributeLine.search([('product_tmpl_id', '=', mitad.id)])

print(f"\n  Verification:")
print(f"    Variants: {len(variants_after)} (should be 1)")
print(f"    PTAVs: {len(ptavs_after)} (should be 0)")
print(f"    Attribute lines: {len(lines_after)} (should be 0)")

if len(variants_after) == 1 and len(ptavs_after) == 0 and len(lines_after) == 0:
    print(f"\n  ✓ Mitad y Mitad is now a simple product!")
    print(f"    Price: {mitad.list_price}")
else:
    print(f"\n  ⚠ Some references still exist")

print("=" * 70)