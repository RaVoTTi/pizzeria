#!/usr/bin/env python3
"""
Step 4: Create the phantom BoM for Mitad y Mitad.
This is the core of stock deduction.

Architecture:
  - 1x Bollo de Masa (unconditional — always 1 dough, shared by both halves)
  - For each pizza's toppings: 0.5 qty conditioned on Lado A, 0.5 qty conditioned on Lado B
  - When a variant is selected, Odoo keeps only the lines matching that variant's attributes

After this step, verify in Odoo UI:
  - Go to Manufacturing > Products > Mitad y Mitad > BoM
  - You should see 1 unconditional dough line + many conditional topping lines
  - Click "BoM Structure & Cost" and select a variant to see which lines apply

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/step4_bom.py
"""

print("=" * 70)
print("  Step 4: Create Phantom BoM with Conditional Lines")
print("=" * 70)

ProductTemplate = env['product.template']
MrpBom = env['mrp.bom']
Ptav = env['product.template.attribute.value']

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

bollo = ProductTemplate.search([('name', '=', 'Bollo de Masa (Pre-pizza)')], limit=1)
if not bollo:
    print("  ERROR: Bollo de Masa not found!")
    exit(1)
bollo_v = env['product.product'].search([('product_tmpl_id', '=', bollo.id)], limit=1)

# Build ptav map (attribute values linked to the Mitad product)
print("\n  Building ptav map...")
ptav_map = {}
for pizza_name in MITAD_PIZZAS:
    pizza = ProductTemplate.search([('name', '=', pizza_name)], limit=1)
    if not pizza:
        print(f"  WARNING: {pizza_name} not found, skipping")
        continue

    bom = MrpBom.search([('product_tmpl_id', '=', pizza.id), ('type', '=', 'phantom')], limit=1)
    if not bom:
        print(f"  WARNING: No phantom BoM for {pizza_name}, skipping")
        continue

    # Find the ptav for this pizza name on each attribute
    ptav_a = Ptav.search([
        ('product_tmpl_id', '=', mitad.id),
        ('product_attribute_value_id.name', '=', pizza_name),
        ('product_attribute_value_id.attribute_id.name', '=', 'Lado A'),
    ], limit=1)
    ptav_b = Ptav.search([
        ('product_tmpl_id', '=', mitad.id),
        ('product_attribute_value_id.name', '=', pizza_name),
        ('product_attribute_value_id.attribute_id.name', '=', 'Lado B'),
    ], limit=1)

    if not ptav_a or not ptav_b:
        print(f"  WARNING: ptav not found for {pizza_name} (A={ptav_a.id if ptav_a else 'NONE'}, B={ptav_b.id if ptav_b else 'NONE'})")
        continue

    ptav_map[pizza_name] = {
        'ptav_a': ptav_a,
        'ptav_b': ptav_b,
        'product': pizza,
        'bom': bom,
        'price': pizza.list_price,
    }
    print(f"  {pizza_name}: ptav_a={ptav_a.id}, ptav_b={ptav_b.id}, toppings={len([l for l in bom.bom_line_ids if l.product_id.product_tmpl_id.id != bollo.id])}")

print(f"\n  Mapped {len(ptav_map)}/{len(MITAD_PIZZAS)} pizzas to ptavs")

# Remove existing BoM
existing_bom = MrpBom.search([('product_tmpl_id', '=', mitad.id)], limit=1)
if existing_bom:
    existing_bom.unlink()
    print(f"  Removed existing BoM")

# Build BoM lines
bom_lines = [(0, 0, {
    'product_id': bollo_v.id,
    'product_qty': 1,
    'product_uom_id': bollo_v.uom_id.id,
})]
print(f"\n  Unconditional line: 1x {bollo_v.display_name}")

topping_count = 0
for pizza_name, data in ptav_map.items():
    bom = data['bom']
    pizza_toppings = 0

    for bom_line in bom.bom_line_ids:
        ingredient = bom_line.product_id

        if ingredient.product_tmpl_id.id == bollo.id:
            continue

        half_qty = bom_line.product_qty * 0.5
        uom_id = bom_line.product_uom_id.id

        bom_lines.append((0, 0, {
            'product_id': ingredient.id,
            'product_qty': half_qty,
            'product_uom_id': uom_id,
            'bom_product_template_attribute_value_ids': [(4, data['ptav_a'].id)],
        }))

        bom_lines.append((0, 0, {
            'product_id': ingredient.id,
            'product_qty': half_qty,
            'product_uom_id': uom_id,
            'bom_product_template_attribute_value_ids': [(4, data['ptav_b'].id)],
        }))

        pizza_toppings += 1

    topping_count += pizza_toppings
    print(f"  {pizza_name}: {pizza_toppings} toppings x 2 sides = {pizza_toppings * 2} conditional lines")

new_bom = MrpBom.create({
    'product_tmpl_id': mitad.id,
    'type': 'phantom',
    'product_qty': 1,
    'code': 'MITAD_Y_MITAD',
    'bom_line_ids': bom_lines,
})

print(f"\n  Created phantom BoM (ID: {new_bom.id})")
print(f"  Total lines: {1 + topping_count * 2}")
print(f"    - 1 unconditional (Bollo de Masa: always 1 dough)")
print(f"    - {topping_count * 2} conditional (toppings at 50%, conditioned on Lado A/B)")
env.cr.commit()

# Verify a specific variant
print(f"\n  VERIFICATION: Checking Mozzarella variant...")
muzza_ptav = ptav_map.get('Mozzarella')
if muzza_ptav:
    print(f"  Example: When Mozzarella is selected on Lado A:")
    for line in new_bom.bom_line_ids:
        if line.bom_product_template_attribute_value_ids:
            ptav_names = [p.product_attribute_value_id.name for p in line.bom_product_template_attribute_value_ids]
            if 'Mozzarella' in ptav_names:
                print(f"    {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name} (conditioned on {ptav_names})")
        else:
            print(f"    {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name} (UNCONDITIONAL)")

print("=" * 70)