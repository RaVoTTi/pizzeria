import csv
import os
import base64
import logging

logger = logging.getLogger(__name__)

CSV_DIR = '/csv'

IMAGES_DIR = '/images/productos'


def encode_image(image_path):
    if not image_path or image_path == 'PEGAR_LINK_AQUI':
        return False
    full_path = image_path if os.path.isabs(image_path) else os.path.join(IMAGES_DIR, image_path)
    if os.path.isfile(full_path):
        with open(full_path, 'rb') as f:
            return base64.b64encode(f.read())
    return False


def csv_rows(filename):
    path = os.path.join(CSV_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


# UoM mapping for standard Odoo UoMs
UOM_SEARCH = {
    'kg': 'kg',
    'L': 'Liter',
    'Unidades': 'Unit',
    'Units': 'Unit',
}


def get_uom_id(env, name):
    """Get UoM ID by name, searching through various options."""
    search_name = UOM_SEARCH.get(name, name)
    rec = env['uom.uom'].search([('name', 'ilike', search_name)], limit=1)
    if rec:
        return rec.id
    rec = env['uom.uom'].search([('name', 'ilike', '%' + name + '%')], limit=1)
    if rec:
        return rec.id
    all_uoms = env['uom.uom'].search([])
    print(f"  WARNING: UoM not found for '{name}', using first available")
    return all_uoms[0].id if all_uoms else False


def get_categ_id(env, categ_ref, cat_ids):
    """Get category ID from reference or name mapping."""
    if categ_ref in cat_ids:
        return cat_ids[categ_ref]

    by_name = {
        'cat_gastos': 'GASTOS OPERATIVOS',
        'cat_servicios': 'Servicios (Luz/Gas)',
        'cat_insumos': 'INSUMOS',
        'cat_barriles': 'Barriles y Gas',
        'cat_mp': 'Materia Prima Cocina',
        'cat_venta': 'VENTAS',
        'cat_bebidas': 'Bebidas sin Alcohol',
        'cat_birra_venta': 'Cerveza Barra',
        'cat_pizzas': 'Pizzas',
        'cat_mitades': 'Mitades',
        'cat_delivery': 'Deliveries',
        'cat_all': 'Todos',
    }
    name = by_name.get(categ_ref)
    if name:
        rec = env['product.category'].search([('name', '=', name)], limit=1)
        if rec:
            return rec.id
    return env.ref('product.product_category_all').id


def find_product_by_name(env, product_name):
    """Find product template ID by name."""
    rec = env['product.template'].search([('name', '=', product_name)], limit=1)
    if rec:
        return rec.id
    return None


# ============================================================================
# MAIN EXECUTION
# ============================================================================

print("=" * 60)
print("  Pizzeria El Gordo - Products, Categories & BoMs Import")
print("=" * 60)

# Load custom UoMs created in initial setup for reference
PINTA_UOM_ID = False
existing_pinta = env['uom.uom'].search([('name', '=', 'Pinta')], limit=1)
if existing_pinta:
    PINTA_UOM_ID = existing_pinta.id
    print(f"\n  Found Pinta UoM (id={PINTA_UOM_ID})")


def get_uom_id_wrapped(env, name):
    """Wrapper to check for custom Pinta UoM first."""
    if name == 'Pinta' and PINTA_UOM_ID:
        return PINTA_UOM_ID
    return get_uom_id(env, name)


print("\n[1/4] Creating product categories...")
cat_rows = csv_rows('categories.csv')
cat_ids = {}

for row in cat_rows:
    existing = env['product.category'].search([('name', '=', row['name'])], limit=1)
    if existing:
        cat_ids[row['id']] = existing.id
        print(f"  Category exists: {row['name']} (id={existing.id})")
        continue

    parent_id = False
    if row.get('parent_id/id'):
        parent_xml = row['parent_id/id']
        if parent_xml in cat_ids:
            parent_id = cat_ids[parent_xml]
        else:
            # Try to find parent by name
            parent_rec = env['product.category'].search([('name', '=', parent_xml)], limit=1)
            if parent_rec:
                parent_id = parent_rec.id

    vals = {'name': row['name']}
    if parent_id:
        vals['parent_id'] = parent_id

    rec = env['product.category'].create(vals)
    cat_ids[row['id']] = rec.id
    print(f"  Created category: {row['name']} (id={rec.id})")

env.cr.commit()

print("\n[2/4] Creating products...")
prod_rows = csv_rows('products.csv')
masa_rows = csv_rows('producto_masa.csv')
all_product_rows = prod_rows + masa_rows

product_ids = {}
product_by_name = {}

for row in all_product_rows:
    external_id = row['id']
    name = row['name']
    categ_ref = row.get('categ_id/id', '')
    detailed_type = row.get('detailed_type', 'product')
    uom_name = row.get('uom_name', 'Unidades')
    standard_price = float(row.get('standard_price', '0') or '0')
    list_price = float(row.get('list_price', '0') or '0')

    existing = env['product.template'].search([('name', '=', name)], limit=1)
    if existing:
        product_ids[external_id] = existing.id
        product_by_name[name] = existing.id
        image_data = encode_image(row.get('image_1920', ''))
        if image_data:
            existing.write({'image_1920': image_data})
            print(f"  Product exists + image updated: {name} (id={existing.id})")
        else:
            print(f"  Product exists: {name} (id={existing.id})")
        continue

    categ_id = get_categ_id(env, categ_ref, cat_ids)
    uom_id = get_uom_id_wrapped(env, uom_name)

    # Map detailed_type to Odoo 19 type field values
    # 'product' -> 'consu' (Goods), 'service' -> 'service', etc.
    type_mapping = {
        'product': 'consu',
        'consu': 'consu',
        'service': 'service',
    }
    product_type = type_mapping.get(detailed_type, 'consu')

    vals = {
        'name': name,
        'categ_id': categ_id,
        'type': product_type,
        'is_storable': product_type != 'service',
        'uom_id': uom_id,
        'standard_price': standard_price,
        'list_price': list_price,
        'sale_ok': list_price > 0,
        'purchase_ok': True,
        'available_in_pos': list_price > 0 and product_type != 'service',
        'taxes_id': [(6, 0, [])],
    }

    image_data = encode_image(row.get('image_1920', ''))
    if image_data:
        vals['image_1920'] = image_data

    rec = env['product.template'].create(vals)
    product_ids[external_id] = rec.id
    product_by_name[name] = rec.id
    print(f"  Created product: {name} (id={rec.id})")

env.cr.commit()

print("\n[3/4] Creating Bill of Materials (BoMs)...")

bollo_rows = csv_rows('receta_del_bollo.csv')
pizza_bom_rows = csv_rows('receta_pizzas_con_masa.csv')
all_bom_rows = bollo_rows + pizza_bom_rows

bom_groups = {}
for row in all_bom_rows:
    key = row['product_tmpl_id/id']
    if key not in bom_groups:
        bom_groups[key] = {
            'code': row.get('code', ''),
            'type': row.get('type', 'phantom'),
            'lines': [],
        }
    bom_groups[key]['lines'].append({
        'product_name': row['bom_line_ids/product_id'],
        'product_qty': float(row['bom_line_ids/product_qty']),
    })

bom_count = 0
for external_id, bom_data in bom_groups.items():
    tmpl_id = product_ids.get(external_id)
    if not tmpl_id:
        print(f"  WARNING: Product not found for BoM: {external_id}")
        continue

    existing_bom = env['mrp.bom'].search([
        ('product_tmpl_id', '=', tmpl_id),
        ('type', '=', bom_data['type']),
    ], limit=1)
    if existing_bom:
        print(f"  BoM already exists for: {external_id}")
        continue

    line_vals = []
    for line in bom_data['lines']:
        line_product_id = find_product_by_name(env, line['product_name'])
        if not line_product_id:
            print(f"    WARNING: Ingredient not found: {line['product_name']}")
            continue
        product_product = env['product.product'].search([
            ('product_tmpl_id', '=', line_product_id)
        ], limit=1)
        if not product_product:
            print(f"    WARNING: No product.product for: {line['product_name']}")
            continue
        line_vals.append((0, 0, {
            'product_id': product_product.id,
            'product_qty': line['product_qty'],
            'product_uom_id': product_product.uom_id.id,
        }))

    if not line_vals:
        print(f"  WARNING: No valid lines for BoM: {external_id}, skipping")
        continue

    bom_vals = {
        'product_tmpl_id': tmpl_id,
        'type': bom_data['type'],
        'code': bom_data.get('code', ''),
        'bom_line_ids': line_vals,
    }
    bom = env['mrp.bom'].create(bom_vals)
    bom_count += 1
    print(f"  Created BoM for: {external_id} ({len(line_vals)} lines)")

env.cr.commit()

print("\n[4/4] Updating POS config for El Gordo...")
pos_config = env['pos.config'].search([], limit=1)
if pos_config:
    # Update name and ensure all products are visible (disable category limits)
    pos_config.write({
        'name': 'Pizzeria El Gordo',
        'limit_categories': False,
    })
    # Clear any existing category restrictions
    if pos_config.iface_available_categ_ids:
        pos_config.write({'iface_available_categ_ids': [(5, 0, 0)]})
    print(f"  Updated POS config: {pos_config.name} (id={pos_config.id})")
    print(f"  Category limits disabled - all products with 'available_in_pos' will be shown")
else:
    print("  No POS config found yet. Create one from the UI after first login.")
    print("  IMPORTANT: After creating POS config, disable 'Limit Categories' in settings")

env.cr.commit()

print("\n[5/5] Enabling products for POS...")
# Ensure all products with list_price > 0 are available in POS
# This handles both newly created and existing products
pos_products = env['product.template'].search([
    ('list_price', '>', 0),
    ('type', '!=', 'service'),
    ('available_in_pos', '=', False),
])
if pos_products:
    pos_products.write({'available_in_pos': True})
    print(f"  Enabled {len(pos_products)} products for POS")
else:
    print("  All products already enabled for POS")

env.cr.commit()

print("\n[6/6] Setting up POS categories...")
# Create POS categories and assign products to hide demo products
pos_categ_mapping = {
    'Pizzas': 'Pizzas',
    'Mitades': 'Mitades',
    'Cerveza Barra': 'Cerveza',
    'Bebidas sin Alcohol': 'Bebidas',
    'VENTAS': 'Empanadas',
}

pos_categs = {}
for product_categ_name, pos_categ_name in pos_categ_mapping.items():
    # Get or create POS category
    pos_categ = env['pos.category'].search([('name', '=', pos_categ_name)], limit=1)
    if not pos_categ:
        pos_categ = env['pos.category'].create({'name': pos_categ_name})
        print(f"  Created POS category: {pos_categ_name}")
    else:
        print(f"  Using existing POS category: {pos_categ_name}")
    pos_categs[product_categ_name] = pos_categ
    
    # Assign products to this POS category
    products = env['product.template'].search([
        ('categ_id.name', '=', product_categ_name),
        ('available_in_pos', '=', True),
    ])
    if products:
        products.write({'pos_categ_ids': [(6, 0, [pos_categ.id])]})
        print(f"    - Assigned {len(products)} products")

# Configure POS to only show these categories (hiding demo products)
pos_config = env['pos.config'].search([], limit=1)
if pos_config and pos_categs:
    pos_categ_ids = [c.id for c in pos_categs.values()]
    pos_config.write({
        'limit_categories': True,
        'iface_available_categ_ids': [(6, 0, pos_categ_ids)],
    })
    print(f"  POS configured to show only your {len(pos_categ_ids)} categories")

env.cr.commit()

print("\n" + "=" * 60)
print("  Products import complete!")
print(f"  Categories created: {len(cat_ids)}")
print(f"  Products created: {len(product_ids)}")
print(f"  BoMs created: {bom_count}")
print("=" * 60)
