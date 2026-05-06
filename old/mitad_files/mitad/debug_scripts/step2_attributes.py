#!/usr/bin/env python3
"""
Step 2: Create attributes Lado A and Lado B with DYNAMIC variant creation.

CRITICAL: 'dynamic' means Odoo creates variants on-demand when selected in POS,
NOT upfront (which would create 18x18=324 variants).

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/step2_attributes.py
"""

print("=" * 70)
print("  Step 2: Create Attributes (dynamic variant creation)")
print("=" * 70)

ProductAttribute = env['product.attribute']
ProductAttrValue = env['product.attribute.value']

MITAD_PIZZAS = [
    'Mozzarella', 'Especial', 'Cuatro quesos ahumado',
    'Rucula y jamon crudo', 'Rucula veggie', 'Napolitana con ajo',
    'Napolitana vegana', 'Pepperoni', 'Fugazzeta',
    'Grinch (fugazzeta con pesto)', 'Caprese', 'Borromeo (panceta)',
    'Super Pesto', 'Champignon', 'Champignon veggie',
    'Palmitos y jamon', 'Anana', 'Anchoas',
]

# Create attributes
for attr_name in ['Lado A', 'Lado B']:
    attr = ProductAttribute.search([('name', '=', attr_name)], limit=1)
    if attr:
        if attr.create_variant == 'dynamic':
            print(f"  OK: {attr_name} already exists with create_variant=dynamic (ID: {attr.id})")
        else:
            print(f"  WARNING: {attr_name} exists with create_variant={attr.create_variant}")
            print(f"  Run step0_cleanup.py first, then re-run this step.")
            exit(1)
    else:
        attr = ProductAttribute.create({
            'name': attr_name,
            'display_type': 'radio',
            'create_variant': 'dynamic',
        })
        print(f"  Created: {attr_name} (ID: {attr.id}, dynamic)")

attr_a = ProductAttribute.search([('name', '=', 'Lado A')], limit=1)
attr_b = ProductAttribute.search([('name', '=', 'Lado B')], limit=1)

# Create values
print(f"\n  Creating attribute values...")
for pizza_name in MITAD_PIZZAS:
    for attr, label in [(attr_a, 'A'), (attr_b, 'B')]:
        val = ProductAttrValue.search([
            ('name', '=', pizza_name),
            ('attribute_id', '=', attr.id),
        ], limit=1)
        if not val:
            val = ProductAttrValue.create({
                'name': pizza_name,
                'attribute_id': attr.id,
            })
            print(f"    Created: {pizza_name} (Lado {label}, ID: {val.id})")

val_count_a = ProductAttrValue.search([('attribute_id', '=', attr_a.id)])
val_count_b = ProductAttrValue.search([('attribute_id', '=', attr_b.id)])
print(f"\n  Lado A values: {len(val_count_a)}")
print(f"  Lado B values: {len(val_count_b)}")

env.cr.commit()
print("\n  Attributes created. Proceed to step 3.")
print("=" * 70)