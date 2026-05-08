#!/usr/bin/env python3
"""Check product types and fix storable flag for ingredients."""

print("=" * 70)
print("  Checking Product Types")
print("=" * 70)

# Check current state
storable = env['product.product'].search([('is_storable', '=', True)])
consu = env['product.product'].search([('type', '=', 'consu')])

print(f"\n  Storable products: {len(storable)}")
if storable:
    for p in storable[:5]:
        print(f"    - {p.display_name}")

print(f"\n  Consumable products: {len(consu)}")
if consu:
    for p in consu[:5]:
        print(f"    - {p.display_name}")

# Find ingredients (products in 'INSUMOS' category or with standard_price > 0 but list_price = 0)
ingredients = env['product.template'].search([
    '|',
    ('categ_id.name', 'ilike', 'INSUMOS'),
    '&', ('standard_price', '>', 0), ('list_price', '=', 0)
])

print(f"\n  Ingredients found: {len(ingredients)}")
for p in ingredients[:10]:
    print(f"    - {p.name}: type={p.type}, storable={p.is_storable}")

# Count how many need to be changed
need_change = [p for p in ingredients if p.type != 'product']
print(f"\n  Ingredients needing type change (consu→product): {len(need_change)}")

if need_change:
    print("\n  Converting to storable products...")
    for p in need_change:
        p.write({'type': 'product'})
        print(f"    ✓ {p.name}")
    env.cr.commit()
    print(f"\n  Updated {len(need_change)} products to type='product'")
else:
    print("\n  All ingredients already storable")

print("=" * 70)