#!/usr/bin/env python3
"""
Setup Mitad y Mitad (Half & Half) Pizza functionality for Pizzeria El Gordo.

Architecture (follows the chat.md graph):
  - Dynamic variant creation (no upfront 324-variant explosion)
  - Phantom BoM with conditional lines (native Odoo stock deduction)
  - JS module for MAX pricing (instant in POS, works offline for existing variants)
  - Fallback base price = most expensive pizza (safety net)

  POS Screen
      |
      +-- Fast Path (80%) --> Standard Pizza --> Phantom BoM (full recipe)
      |                                           --> Stock Deduction (exact)
      |                                           --> Kitchen Ticket
      |
      +-- Custom Path (20%) --> Mitad y Mitad --> Attribute Selector (Lado A / Lado B)
                                            --> Phantom BoM (conditional qty * 0.5)
                                            --> Stock Deduction (0.5 + 0.5)
                                            --> Kitchen Ticket
                                            --> JS Pricing: MAX(price_A, price_B)

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_mitad_mitad.py

Prerequisites:
    - Must run AFTER import_products.py (needs pizzas and BoMs to exist)
    - Must have point_of_sale and mrp modules installed
"""

import logging

logger = logging.getLogger(__name__)

print("=" * 70)
print("  Setting up Mitad y Mitad (Half & Half Pizzas)")
print("  Architecture: Dynamic Variants + Phantom BoM + JS MAX Pricing")
print("=" * 70)

# ============================================================================
# CONFIGURATION
# ============================================================================

MITAD_PIZZAS = [
    'Mozzarella',
    'Especial',
    'Cuatro quesos ahumado',
    'Rucula y jamon crudo',
    'Rucula veggie',
    'Napolitana con ajo',
    'Napolitana vegana',
    'Pepperoni',
    'Fugazzeta',
    'Grinch (fugazzeta con pesto)',
    'Caprese',
    'Borromeo (panceta)',
    'Super Pesto',
    'Champignon',
    'Champignon veggie',
    'Palmitos y jamon',
    'Anana',
    'Anchoas',
]

MITAD_PRODUCT_NAME = '🍕 Mitad y Mitad'

# ============================================================================
# STEP 1: Find products
# ============================================================================
print("\n[1/6] Finding products...")

ProductTemplate = env['product.template']
ProductAttribute = env['product.attribute']
ProductAttrValue = env['product.attribute.value']
PtalLine = env['product.template.attribute.line']
Ptav = env['product.template.attribute.value']
MrpBom = env['mrp.bom']

mitad_product = ProductTemplate.search([('name', '=', MITAD_PRODUCT_NAME)], limit=1)
if not mitad_product:
    print(f"  ERROR: Product '{MITAD_PRODUCT_NAME}' not found!")
    print("  Make sure import_products.py was run first.")
    exit(1)
print(f"  Found: {mitad_product.name} (ID: {mitad_product.id})")

bollo_product = ProductTemplate.search([('name', '=', 'Bollo de Masa (Pre-pizza)')], limit=1)
if not bollo_product:
    print("  ERROR: Bollo de Masa product not found!")
    exit(1)
bollo_variant = env['product.product'].search([('product_tmpl_id', '=', bollo_product.id)], limit=1)
print(f"  Found: {bollo_product.name} (ID: {bollo_product.id})")

pizza_data = {}
skipped = []
for pizza_name in MITAD_PIZZAS:
    pizza = ProductTemplate.search([('name', '=', pizza_name)], limit=1)
    if not pizza:
        skipped.append(pizza_name)
        print(f"  WARNING: Pizza '{pizza_name}' not found, skipping...")
        continue

    bom = MrpBom.search([
        ('product_tmpl_id', '=', pizza.id),
        ('type', '=', 'phantom'),
    ], limit=1)

    if not bom:
        skipped.append(pizza_name)
        print(f"  WARNING: No phantom BoM for '{pizza_name}', skipping...")
        continue

    pizza_data[pizza_name] = {
        'product': pizza,
        'bom': bom,
        'price': pizza.list_price,
    }
    print(f"  Found: {pizza_name} (price: {pizza.list_price}, ingredients: {len(bom.bom_line_ids)})")

if skipped:
    print(f"\n  Skipped pizzas: {skipped}")

FALLBACK_PRICE = max(data['price'] for data in pizza_data.values()) if pizza_data else 27000
print(f"\n  Eligible pizzas: {len(pizza_data)}")
print(f"  Fallback price (most expensive): {FALLBACK_PRICE}")

# ============================================================================
# STEP 2: Create Attributes with DYNAMIC variant creation
# ============================================================================
# If attributes already exist with 'always' (from a previous run), we must
# remove them from the product first, then recreate with 'dynamic'.
# Odoo does NOT allow changing create_variant on attributes linked to products.
print("\n[2/6] Creating attributes (dynamic variant creation)...")

AttributeLine = env['product.template.attribute.line']

for attr_name in ['Lado A', 'Lado B']:
    existing_attr = ProductAttribute.search([('name', '=', attr_name)], limit=1)
    if existing_attr and existing_attr.create_variant != 'dynamic':
        old_mode = existing_attr.create_variant
        existing_line = AttributeLine.search([
            ('product_tmpl_id', '=', mitad_product.id),
            ('attribute_id', '=', existing_attr.id),
        ], limit=1)
        if existing_line:
            existing_line.unlink()
            print(f"  Removed attribute line for {attr_name} from product")
        existing_attr.unlink()
        print(f"  Deleted old {attr_name} attribute (was '{old_mode}')")
        env.cr.commit()

attr_a = ProductAttribute.search([('name', '=', 'Lado A')], limit=1)
if not attr_a:
    attr_a = ProductAttribute.create({
        'name': 'Lado A',
        'display_type': 'radio',
        'create_variant': 'dynamic',
    })
    print(f"  Created attribute: Lado A (dynamic)")
else:
    print(f"  Found existing: Lado A (create_variant={attr_a.create_variant})")

attr_b = ProductAttribute.search([('name', '=', 'Lado B')], limit=1)
if not attr_b:
    attr_b = ProductAttribute.create({
        'name': 'Lado B',
        'display_type': 'radio',
        'create_variant': 'dynamic',
    })
    print(f"  Created attribute: Lado B (dynamic)")
else:
    print(f"  Found existing: Lado B (create_variant={attr_b.create_variant})")

# ============================================================================
# STEP 3: Create Attribute Values
# ============================================================================
print("\n[3/6] Creating attribute values...")

val_map = {}
for pizza_name in pizza_data:
    val_a = ProductAttrValue.search([
        ('name', '=', pizza_name),
        ('attribute_id', '=', attr_a.id),
    ], limit=1)
    if not val_a:
        val_a = ProductAttrValue.create({
            'name': pizza_name,
            'attribute_id': attr_a.id,
        })

    val_b = ProductAttrValue.search([
        ('name', '=', pizza_name),
        ('attribute_id', '=', attr_b.id),
    ], limit=1)
    if not val_b:
        val_b = ProductAttrValue.create({
            'name': pizza_name,
            'attribute_id': attr_b.id,
        })

    val_map[pizza_name] = {'val_a': val_a, 'val_b': val_b}
    print(f"  {pizza_name}: Lado A (ID:{val_a.id}), Lado B (ID:{val_b.id})")

print(f"  Total: {len(val_map)} pizza options per side")

# ============================================================================
# STEP 4: Link Attributes to Product
# ============================================================================
print("\n[4/6] Linking attributes to Mitad y Mitad product...")

all_val_a_ids = [v['val_a'].id for v in val_map.values()]
all_val_b_ids = [v['val_b'].id for v in val_map.values()]

line_a = PtalLine.search([
    ('product_tmpl_id', '=', mitad_product.id),
    ('attribute_id', '=', attr_a.id),
], limit=1)
if line_a:
    line_a.write({'value_ids': [(6, 0, all_val_a_ids)]})
    print(f"  Updated Lado A: {len(all_val_a_ids)} values")
else:
    line_a = PtalLine.create({
        'product_tmpl_id': mitad_product.id,
        'attribute_id': attr_a.id,
        'value_ids': [(6, 0, all_val_a_ids)],
    })
    print(f"  Created Lado A: {len(all_val_a_ids)} values")

line_b = PtalLine.search([
    ('product_tmpl_id', '=', mitad_product.id),
    ('attribute_id', '=', attr_b.id),
], limit=1)
if line_b:
    line_b.write({'value_ids': [(6, 0, all_val_b_ids)]})
    print(f"  Updated Lado B: {len(all_val_b_ids)} values")
else:
    line_b = PtalLine.create({
        'product_tmpl_id': mitad_product.id,
        'attribute_id': attr_b.id,
        'value_ids': [(6, 0, all_val_b_ids)],
    })
    print(f"  Created Lado B: {len(all_val_b_ids)} values")

env.invalidate_all()

mitad_product.write({
    'list_price': FALLBACK_PRICE,
    'available_in_pos': True,
})
print(f"  Set fallback price: {FALLBACK_PRICE}")
print(f"  Enabled for POS")

var_count = len(mitad_product.product_variant_ids)
print(f"  Product variants (0 dynamic, created on demand): {var_count}")

env.cr.commit()

# ============================================================================
# STEP 5: Build ptav map (product.template.attribute.value)
# ============================================================================
print("\n[5/6] Building attribute value map for BoM conditioning...")

ptav_map = {}
for pizza_name, vals in val_map.items():
    ptav_a = Ptav.search([
        ('product_tmpl_id', '=', mitad_product.id),
        ('product_attribute_value_id', '=', vals['val_a'].id),
    ], limit=1)

    ptav_b = Ptav.search([
        ('product_tmpl_id', '=', mitad_product.id),
        ('product_attribute_value_id', '=', vals['val_b'].id),
    ], limit=1)

    if ptav_a and ptav_b:
        ptav_map[pizza_name] = {'ptav_a': ptav_a, 'ptav_b': ptav_b}
        print(f"  {pizza_name}: ptav_a={ptav_a.id}, ptav_b={ptav_b.id}")
    else:
        print(f"  WARNING: ptav not found for '{pizza_name}', will skip BoM lines")

# ============================================================================
# STEP 6: Create Phantom BoM with conditional lines
# ============================================================================
print("\n[6/6] Creating Phantom BoM with conditional lines...")

existing_bom = MrpBom.search([
    ('product_tmpl_id', '=', mitad_product.id),
], limit=1)
if existing_bom:
    existing_bom.unlink()
    print(f"  Removed existing BoM")

bom_lines = [(0, 0, {
    'product_id': bollo_variant.id,
    'product_qty': 1,
    'product_uom_id': bollo_variant.uom_id.id,
})]

topping_lines = 0
for pizza_name, data in pizza_data.items():
    ptav = ptav_map.get(pizza_name)
    if not ptav:
        print(f"  Skipping {pizza_name} (no ptav)")
        continue

    bom = data['bom']
    topping_count = 0

    for bom_line in bom.bom_line_ids:
        ingredient = bom_line.product_id

        if ingredient.product_tmpl_id.id == bollo_product.id:
            continue

        half_qty = bom_line.product_qty * 0.5
        uom_id = bom_line.product_uom_id.id

        bom_lines.append((0, 0, {
            'product_id': ingredient.id,
            'product_qty': half_qty,
            'product_uom_id': uom_id,
            'bom_product_template_attribute_value_ids': [(4, ptav['ptav_a'].id)],
        }))

        bom_lines.append((0, 0, {
            'product_id': ingredient.id,
            'product_qty': half_qty,
            'product_uom_id': uom_id,
            'bom_product_template_attribute_value_ids': [(4, ptav['ptav_b'].id)],
        }))

        topping_count += 1

    topping_lines += topping_count
    print(f"  {pizza_name}: {topping_count} toppings x 2 sides = {topping_count * 2} conditional lines")

new_bom = MrpBom.create({
    'product_tmpl_id': mitad_product.id,
    'type': 'phantom',
    'product_qty': 1,
    'code': 'MITAD_Y_MITAD',
    'bom_line_ids': bom_lines,
})

print(f"\n  Created phantom BoM (ID: {new_bom.id})")
print(f"  Total lines: {1 + topping_lines * 2}")
print(f"    - 1 unconditional (Bollo de Masa)")
print(f"    - {topping_lines * 2} conditional (toppings at 50%, conditioned on Lado A/B)")

env.cr.commit()

# ============================================================================
# CLEANUP: Remove old server actions (no longer needed)
# ============================================================================
print("\n  Cleaning up old server actions (no longer needed)...")

ServerAction = env['ir.actions.server']
BaseAutomation = env['base.automation']

removed = 0
for action_name in ['Mitad y Mitad - MAX Pricing', 'Mitad y Mitad - Stock Deduction']:
    for action in ServerAction.search([('name', '=', action_name)]):
        action.unlink()
        removed += 1
        print(f"  Removed server action: {action_name}")

for auto_name in ['Mitad y Mitad - Price on Create', 'Mitad y Mitad - Price on Write', 'Mitad y Mitad - Stock on Paid']:
    for auto in BaseAutomation.search([('name', '=', auto_name)]):
        auto.unlink()
        removed += 1
        print(f"  Removed automation: {auto_name}")

if removed:
    env.cr.commit()
    print(f"  Removed {removed} old actions/automations")
else:
    print("  No old actions found (clean install)")

# ============================================================================
# UoM PRECISION CHECK
# ============================================================================
print("\n  Checking UoM precision for fractional quantities...")

for uom_ref, expected_precision in [
    ('uom.product_uom_gram', 0.001),
    ('uom.product_uom_kilo', 0.01),
]:
    try:
        uom = env.ref(uom_ref)
        if uom and uom.rounding > expected_precision:
            uom.write({'rounding': expected_precision})
            print(f"  Updated {uom.name} rounding to {expected_precision}")
        elif uom:
            print(f"  {uom.name}: rounding={uom.rounding} (OK)")
    except Exception:
        print(f"  Skipped {uom_ref} (not found)")

unit_uom = env['uom.uom'].search([('name', '=', 'Unit')], limit=1)
if unit_uom and unit_uom.rounding > 0.01:
    unit_uom.write({'rounding': 0.01})
    print(f"  Updated Unit rounding to 0.01")

env.cr.commit()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("  Mitad y Mitad Setup Complete!")
print("=" * 70)
print(f"\n  Product: {MITAD_PRODUCT_NAME}")
print(f"  Fallback price: {FALLBACK_PRICE} (most expensive pizza)")
print(f"  Pizza options per side: {len(pizza_data)}")
print(f"  Variant creation: DYNAMIC (created on demand, not upfront)")
print(f"  Stock deduction: Native phantom BoM with conditional lines")
print(f"  Pricing: JS module pos_half_pizza (MAX of selected sides)")
print(f"\n  Architecture:")
print(f"    - Dough: 1 unit (unconditional, shared by both halves)")
print(f"    - Toppings: 50% of original qty (conditioned on Lado A/B)")
print(f"    - Pricing: JS override in POS = MAX(price_A, price_B)")
print(f"    - Fallback: Base price = {FALLBACK_PRICE} (safety if JS fails)")
print(f"\n  NEXT STEP: Install the pos_half_pizza module:")
print(f"    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf \\")
print(f"      -d elgordo -i pos_half_pizza")
print("=" * 70)