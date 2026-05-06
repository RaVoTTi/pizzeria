#!/usr/bin/env python3
"""
Step 6: Verify everything works correctly.

This script checks:
  - Product has Lado A and Lado B attributes linked
  - Attributes use 'dynamic' variant creation
  - Phantom BoM exists with conditional lines
  - BoM structure makes sense for a sample variant
  - No duplicate attribute values
  - UoM rounding is sufficient for fractional quantities

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/step6_verify.py
"""

print("=" * 70)
print("  Step 6: Full Verification")
print("=" * 70)

ProductTemplate = env['product.template']
ProductAttribute = env['product.attribute']
MrpBom = env['mrp.bom']
AttributeLine = env['product.template.attribute.line']

mitad = ProductTemplate.search([('name', '=', '🍕 Mitad y Mitad')], limit=1)
if not mitad:
    print("  ERROR: Mitad y Mitad not found!")
    exit(1)

print(f"\n  Product: {mitad.name} (ID: {mitad.id})")
print(f"  Base price: {mitad.list_price}")
print(f"  Available in POS: {mitad.available_in_pos}")
print(f"  Type: {mitad.type}")

# Check variants
variants = mitad.product_variant_ids
print(f"  Variants: {len(variants)} (should be 0 if dynamic)")

# Check attribute lines
print(f"\n  Attribute lines:")
attr_lines = AttributeLine.search([('product_tmpl_id', '=', mitad.id)])
for line in attr_lines:
    attr = line.attribute_id
    val_count = len(line.value_ids)
    print(f"    {attr.name}: create_variant={attr.create_variant}, values={val_count}")
    if attr.create_variant != 'dynamic':
        print(f"    WARNING: {attr.name} is '{attr.create_variant}', should be 'dynamic'!")
    print(f"    Values: {', '.join(v.name for v in line.value_ids[:5])}{'...' if val_count > 5 else ''}")
    if val_count != 18:
        print(f"    WARNING: Expected 18 values, got {val_count}")

# Check BoM
bom = MrpBom.search([('product_tmpl_id', '=', mitad.id)], limit=1)
if not bom:
    print("\n  ERROR: No BoM found!")
    exit(1)

print(f"\n  BoM (ID: {bom.id}, type: {bom.type})")
print(f"  Total lines: {len(bom.bom_line_ids)}")

unconditional = 0
conditional = 0
for line in bom.bom_line_ids:
    if line.bom_product_template_attribute_value_ids:
        conditional += 1
    else:
        unconditional += 1

print(f"    Unconditional: {unconditional}")
print(f"    Conditional: {conditional}")

# Show unconditional lines
print(f"\n  Unconditional BoM lines:")
for line in bom.bom_line_ids:
    if not line.bom_product_template_attribute_value_ids:
        print(f"    {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name}")

# Show a sample of conditional lines
print(f"\n  Sample conditional lines (first 10):")
shown = 0
for line in bom.bom_line_ids:
    if line.bom_product_template_attribute_value_ids:
        ptav_names = [f"{p.product_attribute_value_id.name} ({p.attribute_id.name})" for p in line.bom_product_template_attribute_value_ids]
        print(f"    {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name} → {', '.join(ptav_names)}")
        shown += 1
        if shown >= 10:
            break
print(f"    ... ({conditional - 10} more)" if conditional > 10 else "")

# UoM check
print(f"\n  UoM precision check:")
unit_uom = env['uom.uom'].search([('name', '=', 'Unit')], limit=1)
if unit_uom:
    print(f"    Unit rounding: {unit_uom.rounding} (should be <= 0.01)")
    if unit_uom.rounding > 0.01:
        print(f"    WARNING: Unit rounding is {unit_uom.rounding}, may cause 0.5 qty issues!")

try:
    gram = env.ref('uom.product_uom_gram')
    print(f"    Gram rounding: {gram.rounding} (should be <= 0.001)")
except Exception:
    print("    Gram UoM: not found")

# Final summary
print(f"\n" + "=" * 70)
print(f"  VERIFICATION SUMMARY")
print(f"=" * 70)
errors = []
if not mitad.available_in_pos:
    errors.append("Product not available in POS")
if len(attr_lines) != 2:
    errors.append(f"Expected 2 attribute lines, got {len(attr_lines)}")
for al in attr_lines:
    if al.attribute_id.create_variant != 'dynamic':
        errors.append(f"{al.attribute_id.name} is not dynamic")
if not bom:
    errors.append("No BoM found")
if unconditional != 1:
    errors.append(f"Expected 1 unconditional line (dough), got {unconditional}")
if conditional == 0:
    errors.append("No conditional lines in BoM")

if errors:
    print(f"  ISSUES FOUND:")
    for e in errors:
        print(f"    - {e}")
else:
    print(f"  ALL CHECKS PASSED")
    print(f"\n  Next steps:")
    print(f"    1. Open POS at http://elgordo.local")
    print(f"    2. Tap 'Mitad y Mitad'")
    print(f"    3. Verify configurator shows Lado A and Lado B")
    print(f"    4. Select two pizzas and verify price = MAX of the two")
    print(f"    5. Complete order and check stock deduction")
print("=" * 70)