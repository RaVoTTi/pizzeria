#!/usr/bin/env python3
"""
Step 5: Set prices on attribute values (price_extra = difference from base).

This is the ONLY way Odoo variant pricing works natively:
  final_price = base_price + sum(price_extra for selected attribute values)

For Mitad y Mitad:
  - Base price = 12000 (cheapest pizza, Mozzarella)
  - Each pizza's price_extra = its list_price - 12000

When the JS module works: MAX(price_A, price_B) is applied.
When the JS module fails: price = 12000 + max(extra_A, extra_B) is still close,
  but actually = 12000 + extra_A + extra_B which is WRONG.
  That's why we set base price to the most expensive pizza ($18000) as safety fallback.

IMPORTANT: Check step6 notes about JS pricing.

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/step5_price_extra.py
"""

print("=" * 70)
print("  Step 5: Set Price Extras on Attribute Values")
print("=" * 70)

ProductTemplate = env['product.template']
ProductAttribute = env['product.attribute']
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

# Get current base price (fallback)
base_price = mitad.list_price
print(f"  Current base price: {base_price}")

print(f"\n  Setting price_extra for each attribute value:")
print(f"  format: pizza_name → price_extra = list_price - base_price")

updated = 0
for pizza_name in MITAD_PIZZAS:
    pizza = ProductTemplate.search([('name', '=', pizza_name)], limit=1)
    if not pizza:
        print(f"  WARNING: {pizza_name} not found")
        continue

    price_extra = pizza.list_price - base_price

    for lado in ['Lado A', 'Lado B']:
        ptav = Ptav.search([
            ('product_tmpl_id', '=', mitad.id),
            ('product_attribute_value_id.name', '=', pizza_name),
            ('product_attribute_value_id.attribute_id.name', '=', lado),
        ], limit=1)

        if ptav:
            ptav.write({'price_extra': price_extra})
            updated += 1
            if price_extra != 0:
                print(f"    {pizza_name} ({lado}): price_extra = {price_extra}")
        else:
            print(f"    WARNING: ptav not found for {pizza_name} ({lado})")

env.cr.commit()

print(f"\n  Updated {updated} ptav records with price_extra values")
print(f"\n  NOTE: These price_extras are NOT used for MAX pricing.")
print(f"  The JS module (pos_half_pizza) overrides pricing to MAX(price_A, price_B).")
print(f"  The base price ({base_price}) is the fallback if JS fails.")
print("=" * 70)