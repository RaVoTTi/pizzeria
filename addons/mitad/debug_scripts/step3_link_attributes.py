#!/usr/bin/env python3
"""
Step 3: Link attributes Lado A and Lado B to the Mitad y Mitad product.
This makes the product configurator appear in POS.

After this step, verify in Odoo UI:
  - Go to Product > Mitad y Mitad > Variants tab
  - You should see Lado A and Lado B as attribute lines
  - NO variants should exist yet (dynamic = created on demand)

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/step3_link_attributes.py
"""

print("=" * 70)
print("  Step 3: Link Attributes to Product")
print("=" * 70)

ProductTemplate = env['product.template']
ProductAttribute = env['product.attribute']
ProductAttrValue = env['product.attribute.value']
AttributeLine = env['product.template.attribute.line']

MITAD_PIZZAS = [
    'Mozzarella', 'Especial', 'Cuatro quesos ahumado',
    'Rucula y jamon crudo', 'Rucula veggie', 'Napolitana con ajo',
    'Napolitana vegana', 'Pepperoni', 'Fugazzeta',
    'Grinch (fugazzeta con pesto)', 'Caprese', 'Borromeo (panceta)',
    'Super Pesto', 'Champignon', 'Champignon veggie',
    'Palmitos y jamon', 'Anana', 'Anchoas',
]

mitad = ProductTemplate.search([('name', '=', '🍕 Mitad y Mitad')], limit=1)
if not mitad:
    print("  ERROR: Mitad y Mitad not found!")
    exit(1)

attr_a = ProductAttribute.search([('name', '=', 'Lado A')], limit=1)
attr_b = ProductAttribute.search([('name', '=', 'Lado B')], limit=1)
if not attr_a or not attr_b:
    print("  ERROR: Run step2_attributes.py first!")
    exit(1)

# Collect value IDs
val_a_ids = []
val_b_ids = []
for pizza_name in MITAD_PIZZAS:
    va = ProductAttrValue.search([('name', '=', pizza_name), ('attribute_id', '=', attr_a.id)], limit=1)
    vb = ProductAttrValue.search([('name', '=', pizza_name), ('attribute_id', '=', attr_b.id)], limit=1)
    if va:
        val_a_ids.append(va.id)
    if vb:
        val_b_ids.append(vb.id)

print(f"  Collected {len(val_a_ids)} values for Lado A")
print(f"  Collected {len(val_b_ids)} values for Lado B")

# Link Lado A
line_a = AttributeLine.search([
    ('product_tmpl_id', '=', mitad.id),
    ('attribute_id', '=', attr_a.id),
], limit=1)
if line_a:
    line_a.write({'value_ids': [(6, 0, val_a_ids)]})
    print(f"  Updated Lado A attribute line ({len(val_a_ids)} values)")
else:
    line_a = AttributeLine.create({
        'product_tmpl_id': mitad.id,
        'attribute_id': attr_a.id,
        'value_ids': [(6, 0, val_a_ids)],
    })
    print(f"  Created Lado A attribute line ({len(val_a_ids)} values)")

# Link Lado B
line_b = AttributeLine.search([
    ('product_tmpl_id', '=', mitad.id),
    ('attribute_id', '=', attr_b.id),
], limit=1)
if line_b:
    line_b.write({'value_ids': [(6, 0, val_b_ids)]})
    print(f"  Updated Lado B attribute line ({len(val_b_ids)} values)")
else:
    line_b = AttributeLine.create({
        'product_tmpl_id': mitad.id,
        'attribute_id': attr_b.id,
        'value_ids': [(6, 0, val_b_ids)],
    })
    print(f"  Created Lado B attribute line ({len(val_b_ids)} values)")

# Set fallback price and POS visibility
FALLBACK_PRICE = 18000
mitad.write({
    'list_price': FALLBACK_PRICE,
    'available_in_pos': True,
})
print(f"  Set fallback price: {FALLBACK_PRICE}")
print(f"  Available in POS: True")

env.invalidate_all()
env.cr.commit()

# Verify
env.invalidate_all()
mitad = ProductTemplate.search([('name', '=', '🍕 Mitad y Mitad')], limit=1)
variant_count = len(mitad.product_variant_ids)
print(f"\n  Variants created: {variant_count}")
print(f"  (Should be 0 — dynamic variants are created on demand)")
print(f"\n  VERIFY: Go to Product > Mitad y Mitad > Variants tab in Odoo UI")
print(f"  You should see Lado A and Lado B with all pizza options.")
print("=" * 70)