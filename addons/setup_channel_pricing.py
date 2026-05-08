print("=" * 70)
print("  Pizzeria El Gordo - POS Category Setup")
print("=" * 70)

# ---------------------------------------------------------------------------
# Create POS categories in desired order
# ---------------------------------------------------------------------------
print("\n[1/2] Setting up POS categories...")

categ_list = [
    # (pos_category_name, product_category_name, filter_salon)
    ('[S] Empanadas', 'Empanadas', True),
    ('[S] Pizzas', 'Pizzas', True),
    ('[S] Mitades', 'Mitades', True),
    ('Cerveza', 'Cerveza Barra', False),
    ('Bebidas', 'Bebidas sin Alcohol', False),
    ('Empanadas', 'Empanadas', False),
    ('Pizzas', 'Pizzas', False),
    ('Mitades', 'Mitades', False),
    ('Delivery', None, None),
]

all_cat_ids = []
for cat_name, prod_cat_name, is_salon in categ_list:
    cat = env['pos.category'].search([('name', '=', cat_name)], limit=1)
    if not cat:
        cat = env['pos.category'].create({'name': cat_name})
        print(f"  Created: {cat_name}")
    else:
        print(f"  Exists: {cat_name}")
    all_cat_ids.append(cat.id)

    if prod_cat_name and is_salon is not None:
        domain = [('categ_id.name', '=', prod_cat_name), ('available_in_pos', '=', True)]
        if is_salon:
            domain.append(('name', 'like', '[S]%'))
        else:
            domain.append(('name', 'not like', '[S]%'))
        prods = env['product.template'].search(domain)
        if prods:
            prods.write({'pos_categ_ids': [(6, 0, [cat.id])]})
            print(f"    -> {len(prods)} products")

env.cr.commit()

# ---------------------------------------------------------------------------
# POS config — order is determined by iface_available_categ_ids
# ---------------------------------------------------------------------------
print("\n[2/2] Configuring POS...")

config = env['pos.config'].search([('name', '=', 'Pizzeria El Gordo')], limit=1)
if not config:
    config = env['pos.config'].search([], limit=1)

if config:
    config.write({
        'name': 'Pizzeria El Gordo',
        'limit_categories': True,
        'iface_available_categ_ids': [(6, 0, all_cat_ids)],
        'module_pos_restaurant': True,
    })
    print(f"  Updated: {config.name}")
    print(f"  {len(all_cat_ids)} categories in order:")
    for cid in all_cat_ids:
        c = env['pos.category'].browse(cid)
        n = env['product.template'].search_count([('pos_categ_ids', 'in', [cid]), ('available_in_pos', '=', True)])
        print(f"    {c.name}: {n}")
else:
    print("  ERROR: No POS config found.")

env.cr.commit()

print("\n" + "=" * 70)
print("  Done.")
print("=" * 70)