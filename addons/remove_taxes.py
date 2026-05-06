#!/usr/bin/env python3
"""
Remove sale taxes from all products (pizzerias in Argentina typically
include IVA in the displayed price, so we don't add tax on top).
"""

print("=" * 70)
print("  Removing Sale Taxes from Products")
print("=" * 70)

# Find all sale taxes
sale_taxes = env['account.tax'].search([('type_tax_use', '=', 'sale')])
print(f"\n  Found {len(sale_taxes)} sale taxes:")
for t in sale_taxes:
    print(f"    ID:{t.id} | {t.name} | {t.amount}% | {t.amount_type} | price_include:{t.price_include}")

# Remove taxes from all product templates
products = env['product.template'].search([])
count = 0
for p in products:
    if p.taxes_id:
        p.write({'taxes_id': [(5, 0, 0)]})
        count += 1

print(f"\n  Removed sale taxes from {count} products")

env.cr.commit()

# Verify
pizzas = env['product.template'].search([('categ_id.name', '=', 'Pizzas')])
untaxed = 0
for p in pizzas:
    if not p.taxes_id:
        untaxed += 1
print(f"\n  Verification: {untaxed}/{len(pizzas)} pizzas have no sale taxes")
print("=" * 70)