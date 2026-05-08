exec(open('/mnt/extra-addons/import_lib.py').read())

print("=" * 60)
print("  [2/5] Creating ingredients, drinks, delivery, and Bollo...")
print("=" * 60)

cat_ids = load_category_index(env)
product_ids = {}
product_by_name = {}

# --- Ingredients, drinks, delivery (products.csv) ---
print("\n  Ingredients, drinks, delivery...")
prod_rows = csv_rows('products.csv')

for row in prod_rows:
    external_id = row['id']
    name = row['name']
    detailed_type = row.get('detailed_type', 'product')
    list_price = float(row.get('list_price', '0') or '0')

    existing = env['product.template'].search([('name', '=', name)], limit=1)
    if existing:
        product_ids[external_id] = existing.id
        product_by_name[name] = existing.id
        image_data = encode_image(row.get('image_1920', ''))
        if image_data:
            existing.write({'image_1920': image_data})
            print(f"    Exists + image: {name} (id={existing.id})")
        else:
            print(f"    Exists: {name} (id={existing.id})")
        continue

    categ_id = get_categ_id(env, row.get('categ_id/id', ''), cat_ids)
    uom_id = get_uom_id_wrapped(env, row.get('uom_name', 'Unidades'))
    product_type = TYPE_MAPPING.get(detailed_type, 'consu')

    vals = {
        'name': name,
        'default_code': external_id.upper(),
        'categ_id': categ_id,
        'type': product_type,
        'is_storable': detailed_type == 'product',
        'uom_id': uom_id,
        'standard_price': float(row.get('standard_price', '0') or '0'),
        'list_price': list_price,
        'sale_ok': list_price > 0,
        'purchase_ok': True,
        'available_in_pos': list_price > 0 and product_type != 'service' and name != 'Costo de Envío',
        'taxes_id': [(6, 0, [])],
    }

    image_data = encode_image(row.get('image_1920', ''))
    if image_data:
        vals['image_1920'] = image_data

    rec = env['product.template'].create(vals)
    product_ids[external_id] = rec.id
    product_by_name[name] = rec.id
    storable = "storable" if detailed_type == 'product' else "consu"
    print(f"    Created: {name} [{storable}] (id={rec.id})")

env.cr.commit()

# --- Bollo de Masa (producto_masa.csv) ---
print("\n  Bollo de Masa (intermediate product)...")
bollo_rows = csv_rows('producto_masa.csv')

for row in bollo_rows:
    external_id = row['id']
    name = row['name']
    detailed_type = row.get('detailed_type', 'product')
    list_price = float(row.get('list_price', '0') or '0')

    existing = env['product.template'].search([('name', '=', name)], limit=1)
    if existing:
        product_ids[external_id] = existing.id
        product_by_name[name] = existing.id
        print(f"    Exists: {name} (id={existing.id})")
        continue

    categ_id = get_categ_id(env, row.get('categ_id/id', ''), cat_ids)
    uom_id = get_uom_id_wrapped(env, row.get('uom_name', 'Unidades'))
    product_type = TYPE_MAPPING.get(detailed_type, 'consu')

    vals = {
        'name': name,
        'default_code': external_id.upper(),
        'categ_id': categ_id,
        'type': product_type,
        'is_storable': detailed_type == 'product',
        'uom_id': uom_id,
        'standard_price': float(row.get('standard_price', '0') or '0'),
        'list_price': list_price,
        'sale_ok': False,
        'purchase_ok': False,
        'available_in_pos': False,
        'taxes_id': [(6, 0, [])],
    }

    rec = env['product.template'].create(vals)
    product_ids[external_id] = rec.id
    product_by_name[name] = rec.id
    print(f"    Created: {name} [storable intermediate] (id={rec.id})")

env.cr.commit()
print(f"\n  Products created: {len(product_ids)}")