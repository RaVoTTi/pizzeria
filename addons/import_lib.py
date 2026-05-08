import csv
import os
import base64
import logging

logger = logging.getLogger(__name__)

CSV_DIR = '/csv'
IMAGES_DIR = '/images/productos'

TYPE_MAPPING = {'product': 'consu', 'consu': 'consu', 'service': 'service'}

UOM_SEARCH = {
    'kg': 'kg',
    'L': 'Liter',
    'Unidades': 'Unit',
    'Units': 'Unit',
    'Pinta': 'Pinta',
}


def csv_rows(filename):
    path = os.path.join(CSV_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def encode_image(image_path):
    if not image_path or image_path == 'PEGAR_LINK_AQUI' or image_path.strip() == '':
        return False
    full_path = image_path if os.path.isabs(image_path) else os.path.join(IMAGES_DIR, image_path)
    if os.path.isfile(full_path):
        with open(full_path, 'rb') as f:
            return base64.b64encode(f.read())
    return False


def get_uom_id(env, name):
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


_PINTA_UOM_ID = None


def get_uom_id_wrapped(env, name):
    global _PINTA_UOM_ID
    if name == 'Pinta':
        if _PINTA_UOM_ID is None:
            existing = env['uom.uom'].search([('name', '=', 'Pinta')], limit=1)
            _PINTA_UOM_ID = existing.id if existing else False
        if _PINTA_UOM_ID:
            return _PINTA_UOM_ID
    return get_uom_id(env, name)


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
        'cat_mitades': 'Mitades',
        'cat_delivery': 'Deliveries',
        'cat_emp': 'Empanadas',
        'cat_all': 'Todos',
    }
    name = by_name.get(categ_ref)
    if name:
        rec = env['product.category'].search([('name', '=', name)], limit=1)
        if rec:
            return rec.id
    return env.ref('product.product_category_all').id


def find_product_by_name(env, product_name):
    rec = env['product.template'].search([('name', '=', product_name)], limit=1)
    if rec:
        return rec.id
    return None


def create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=False):
    external_id = row['id']
    name = row['name']
    categ_ref = row.get('categ_id/id', '')
    detailed_type = row.get('detailed_type', 'product')
    uom_name = row.get('uom_name', 'Unidades')
    standard_price = float(row.get('standard_price', '0') or '0')
    list_price = float(row.get('list_price', '0') or '0')

    display_name = name
    display_code = external_id.upper()

    existing = env['product.template'].search([('name', '=', display_name)], limit=1)
    if existing:
        existing.write({'list_price': list_price})
        product_ids[external_id] = existing.id
        product_by_name[display_name] = existing.id
        image_data = encode_image(row.get('image_1920', ''))
        if image_data:
            existing.write({'image_1920': image_data})
        label = "Salon" if is_salon else "Mostrador"
        print(f"  {label} exists: {display_name} ${list_price:.0f} (id={existing.id})")
        return existing.id

    categ_id = get_categ_id(env, categ_ref, cat_ids)
    uom_id = get_uom_id_wrapped(env, uom_name)

    product_type = TYPE_MAPPING.get(detailed_type, 'consu')

    vals = {
        'name': display_name,
        'default_code': display_code,
        'categ_id': categ_id,
        'type': product_type,
        'is_storable': detailed_type == 'product',
        'uom_id': uom_id,
        'standard_price': standard_price,
        'list_price': list_price,
        'sale_ok': True,
        'purchase_ok': detailed_type == 'product' and not is_salon,
        'available_in_pos': True,
        'taxes_id': [(6, 0, [])],
    }

    image_data = encode_image(row.get('image_1920', ''))
    if image_data:
        vals['image_1920'] = image_data

    rec = env['product.template'].create(vals)
    product_ids[external_id] = rec.id
    product_by_name[display_name] = rec.id
    label = "Salon" if is_salon else "Mostrador"
    print(f"  Created {label}: {display_name} ${list_price:.0f} (id={rec.id})")
    return rec.id


def load_product_index(env):
    product_ids = {}
    product_by_name = {}
    for tmpl in env['product.template'].search([]):
        if tmpl.default_code:
            product_ids[tmpl.default_code.lower()] = tmpl.id
        product_by_name[tmpl.name] = tmpl.id
    return product_ids, product_by_name


def load_category_index(env):
    cat_ids = {}
    for cat in env['product.category'].search([]):
        cat_ids[cat.name] = cat.id
    return cat_ids