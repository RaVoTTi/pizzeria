#!/usr/bin/env python3
"""
Step 1: Verify prerequisites - find all products and their BoMs.

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/step1_verify.py
"""

print("=" * 70)
print("  Step 1: Verify Prerequisites")
print("=" * 70)

MITAD_PIZZAS = [
    'Mozzarella', 'Especial', 'Cuatro quesos ahumado',
    'Rucula y jamon crudo', 'Rucula veggie', 'Napolitana con ajo',
    'Napolitana vegana', 'Pepperoni', 'Fugazzeta',
    'Grinch (fugazzeta con pesto)', 'Caprese', 'Borromeo (panceta)',
    'Super Pesto', 'Champignon', 'Champignon veggie',
    'Palmitos y jamon', 'Anana', 'Anchoas',
]

ProductTemplate = env['product.template']
MrpBom = env['mrp.bom']

# Find Mitad y Mitad
mitad = ProductTemplate.search([('name', '=', '🍕 Mitad y Mitad')], limit=1)
if mitad:
    print(f"\n  OK: Mitad y Mitad found (ID: {mitad.id})")
    print(f"       list_price: {mitad.list_price}")
    print(f"       available_in_pos: {mitad.available_in_pos}")
    print(f"       type: {mitad.type}")
    print(f"       variants: {len(mitad.product_variant_ids)}")
else:
    print("\n  ERROR: 🍕 Mitad y Mitad NOT found! Run import_products.py first.")
    exit(1)

# Find Bollo
bollo = ProductTemplate.search([('name', '=', 'Bollo de Masa (Pre-pizza)')], limit=1)
if bollo:
    bollo_v = env['product.product'].search([('product_tmpl_id', '=', bollo.id)], limit=1)
    print(f"  OK: Bollo found (ID: {bollo.id}, variant: {bollo_v.id})")
else:
    print("  ERROR: Bollo de Masa NOT found!")
    exit(1)

# Find each pizza and its BoM
print(f"\n  Checking {len(MITAD_PIZZAS)} pizzas:")
errors = []
pizza_data = {}
for name in MITAD_PIZZAS:
    p = ProductTemplate.search([('name', '=', name)], limit=1)
    if not p:
        errors.append(f"NOT FOUND: {name}")
        continue
    bom = MrpBom.search([('product_tmpl_id', '=', p.id), ('type', '=', 'phantom')], limit=1)
    if not bom:
        errors.append(f"NO PHANTOM BoM: {name}")
        continue
    toppings = [l for l in bom.bom_line_ids if l.product_id.product_tmpl_id.id != bollo.id]
    print(f"    {name}: price={p.list_price}, BoM lines={len(bom.bom_line_ids)}, toppings={len(toppings)}")
    pizza_data[name] = {'product': p, 'bom': bom, 'price': p.list_price}

if errors:
    print(f"\n  ERRORS:")
    for e in errors:
        print(f"    {e}")
    exit(1)

print(f"\n  All {len(pizza_data)}/{len(MITAD_PIZZAS)} pizzas OK")
print(f"  Max price: {max(d['price'] for d in pizza_data.values())}")
print(f"  Min price: {min(d['price'] for d in pizza_data.values())}")
print("=" * 70)