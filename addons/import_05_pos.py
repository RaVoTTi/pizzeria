exec(open('/mnt/extra-addons/import_lib.py').read())

print("=" * 60)
print("  [5/5] Setting up POS categories and config...")
print("=" * 60)

pos_categ_mapping = [
    ('Empanadas', '[S] Empanadas', True),
    ('Pizzas', '[S] Pizzas', True),
    ('Mitades', '[S] Mitades', True),
    ('Paninis', '[S] Paninis', True),
    ('Cerveza Barra', 'Cerveza', False),
    ('Bebidas sin Alcohol', 'Bebidas', False),
    ('Empanadas', 'Empanadas', False),
    ('Pizzas', 'Pizzas', False),
    ('Mitades', 'Mitades', False),
    ('Paninis', 'Paninis', False),
]

all_categ_ids = []
for product_categ_name, pos_categ_name, is_salon in pos_categ_mapping:
    pos_categ = env['pos.category'].search([('name', '=', pos_categ_name)], limit=1)
    if not pos_categ:
        pos_categ = env['pos.category'].create({'name': pos_categ_name})
        print(f"  Created POS category: {pos_categ_name}")
    else:
        print(f"  POS category exists: {pos_categ_name}")
    all_categ_ids.append(pos_categ.id)

    name_filter = ('name', 'like', '[S]%') if is_salon else ('name', 'not like', '[S]%')
    products = env['product.template'].search([
        ('categ_id.name', '=', product_categ_name),
        ('available_in_pos', '=', True),
        name_filter,
    ])
    if products:
        products.write({'pos_categ_ids': [(6, 0, [pos_categ.id])]})
        print(f"    - {len(products)} products")

delivery_prods = env['product.template'].search([('name', 'in', ['Costo de Envío', 'Delivery', 'Envio Cerca', 'Envio Lejos', 'Envio Procrear'])])
delivery_categ = env['pos.category'].search([('name', '=', 'Delivery')], limit=1)
if not delivery_categ:
    delivery_categ = env['pos.category'].create({'name': 'Delivery'})
    print(f"  Created POS category: Delivery")
all_categ_ids.append(delivery_categ.id)
if delivery_prods:
    delivery_prods.write({'pos_categ_ids': [(6, 0, [delivery_categ.id])], 'available_in_pos': True})
    print(f"  Assigned {len(delivery_prods)} Delivery products")

pos_products = env['product.template'].search([
    ('list_price', '>', 0), ('type', '!=', 'service'), ('available_in_pos', '=', False),
])
if pos_products:
    pos_products.write({'available_in_pos': True})
    print(f"\n  Enabled {len(pos_products)} additional products for POS")

env.cr.commit()

print(f"\n  POS categories configured: {len(all_categ_ids)}")