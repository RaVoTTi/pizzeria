import csv
import os
import base64
import logging
import odoo

logger = logging.getLogger(__name__)

CSV_DIR = '/csv'

env = env

def csv_rows(filename):
    path = os.path.join(CSV_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


UOM_SEARCH = {
    'kg': 'kg',
    'L': 'Liter',
    'Unidades': 'Unit',
}


def get_uom_id(env, name):
    search_name = UOM_SEARCH.get(name, name)
    rec = env['uom.uom'].search([('name', 'ilike', search_name)], limit=1)
    if rec:
        return rec.id
    rec = env['uom.uom'].search([('name', 'ilike', '%' + name + '%')], limit=1)
    if rec:
        return rec.id
    all_uoms = env['uom.uom'].search([])
    print(f"  WARNING: UoM not found for '{name}', available: {[u.name for u in all_uoms[:10]]}")
    return all_uoms[0].id if all_uoms else False


def find_or_create_category(env, xml_id):
    parts = xml_id.split('_')
    cat_name = ' '.join(p.capitalize() for p in parts if p not in ('cat',))
    parent_map = {
        'cat_all': None,
        'cat_gastos': 'cat_all',
        'cat_insumos': 'cat_all',
        'cat_venta': 'cat_all',
    }
    parent_xml = parent_map.get(xml_id)
    parent_id = False
    if parent_xml:
        parent_rec = env['product.category'].search([('name', '=', parent_xml)], limit=1)
        if parent_rec:
            parent_id = parent_rec.id
    existing = env['product.category'].search([('name', '=', cat_name)], limit=1)
    if existing:
        return existing.id
    vals = {'name': cat_name}
    if parent_id:
        vals['parent_id'] = parent_id
    rec = env['product.category'].create(vals)
    return rec.id


def get_categ_id(env, categ_ref, cat_ids):
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
        'cat_delivery': 'Deliveries',
        'cat_all': 'Todos',
    }
    name = by_name.get(categ_ref)
    if name:
        rec = env['product.category'].search([('name', '=', name)], limit=1)
        if rec:
            return rec.id
    return env.ref('product.product_category_all').id


def install_modules(env, module_names):
    installed_any = False
    for mod in module_names:
        module = env['ir.module.module'].search([('name', '=', mod)], limit=1)
        if module and module.state != 'installed':
            print(f"Installing module: {mod}")
            module.button_immediate_install()
            installed_any = True
        elif not module:
            logger.warning("Module not found: %s", mod)
    
    if installed_any:
        env.cr.commit()
        # Force a complete registry reload for this database
        registry = odoo.registry(env.cr.dbname)
        # Build a brand new environment using the fresh registry
        new_env = odoo.api.Environment(env.cr, env.uid, env.context)
        return new_env
    
    return env


print("=" * 60)
print("  Pizzeria El Gordo - Data Import Script")
print("=" * 60)

print("\n[1/6] Installing required modules...")
env = install_modules(env, [
    'uom',
    'stock',
    'mrp',
    'point_of_sale',
])

print("\n[2/6] Creating Unit of Measure: Pinta...")
existing_pinta = env['uom.uom'].search([('name', '=', 'Pinta')], limit=1)
if not existing_pinta:
    volume_cat = env['uom.category'].search([('name', 'ilike', 'Volume')], limit=1)
    if not volume_cat:
        volume_cat = env.ref('uom.product_uom_categ_vol')
    pinta = env['uom.uom'].create({
        'name': 'Pinta',
        'category_id': volume_cat.id,
        'uom_type': 'bigger',
        'factor_inv': 0.473,
        'rounding': 0.01,
    })
    PINTA_UOM_ID = pinta.id
    print(f"  Created Pinta UoM (id={PINTA_UOM_ID})")
else:
    PINTA_UOM_ID = existing_pinta.id
    print(f"  Pinta UoM already exists (id={PINTA_UOM_ID})")

def get_uom_id_wrapped(env, name):
    if name == 'Pinta':
        return PINTA_UOM_ID
    return get_uom_id(env, name)

def encode_image(image_path):
    if not image_path or image_path == 'PEGAR_LINK_AQUI':
        return False
    if os.path.isfile(image_path):
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read())
    return False

print("\n[3/6] Creating product categories...")
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
            parent_rec = env['product.category'].search([('name', '=', row['name'])], limit=1)
            if parent_rec:
                parent_id = parent_rec.id
    vals = {'name': row['name']}
    if parent_id:
        vals['parent_id'] = parent_id
    rec = env['product.category'].create(vals)
    cat_ids[row['id']] = rec.id
    print(f"  Created category: {row['name']} (id={rec.id})")

env.cr.commit()

print("\n[4/6] Creating products...")
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

    if detailed_type == 'service':
        is_storable = False
    else:
        is_storable = True

    vals = {
        'name': name,
        'categ_id': categ_id,
        'detailed_type': detailed_type,
        'is_storable': is_storable,
        'uom_id': uom_id,
        'uom_po_id': uom_id,
        'standard_price': standard_price,
        'list_price': list_price,
        'sale_ok': list_price > 0,
        'purchase_ok': True,
        'available_in_pos': list_price > 0 and detailed_type != 'service',
    }

    image_data = encode_image(row.get('image_1920', ''))
    if image_data:
        vals['image_1920'] = image_data

    rec = env['product.template'].create(vals)
    product_ids[external_id] = rec.id
    product_by_name[name] = rec.id
    print(f"  Created product: {name} (id={rec.id})")

env.cr.commit()

print("\n[5/6] Creating Bill of Materials (BoMs)...")

def find_product_by_name(env, product_name):
    rec = env['product.template'].search([('name', '=', product_name)], limit=1)
    if rec:
        return rec.id
    return None

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
    print(f"  Created BoM for: {external_id} ({len(line_vals)} lines)")

env.cr.commit()

print("\n[6/6] Updating POS config for El Gordo...")
pos_config = env['pos.config'].search([], limit=1)
if pos_config:
    pos_config.write({
        'name': 'Pizzeria El Gordo',
    })
    print(f"  Updated POS config: {pos_config.name} (id={pos_config.id})")
else:
    print("  No POS config found yet. Create one from the UI after first login.")

env.cr.commit()

print("\n" + "=" * 60)
print("  Import complete!")
print(f"  Products created: {len(product_ids)}")
print(f"  Categories created: {len(cat_ids)}")
print(f"  BoMs created: {len(bom_groups)}")
print("=" * 60)