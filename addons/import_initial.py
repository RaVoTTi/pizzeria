import csv
import os
import logging

logger = logging.getLogger(__name__)

CSV_DIR = '/csv'


def csv_rows(filename):
    path = os.path.join(CSV_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def find_base_uom(env, name_hints):
    """Find a base UoM by trying different name hints."""
    for hint in name_hints:
        uom = env['uom.uom'].search([('name', 'ilike', hint)], limit=1)
        if uom:
            return uom
    return None


def create_uom_from_csv(env, row):
    """Create a single Unit of Measure from CSV row data for Odoo 19."""
    external_id = row['id']
    name = row['name']

    # Check if UoM already exists by name
    existing = env['uom.uom'].search([('name', '=', name)], limit=1)
    if existing:
        print(f"  UoM already exists: {name} (id={existing.id})")
        return existing.id

    # In Odoo 19, UoMs use hierarchical structure with relative_uom_id
    # We need to find a base UoM to link to
    # For Pinta (beer glass), we want to link to Liter (L)
    
    # Map CSV category hints to base UoM names
    category_hint = row.get('category_id/id', '')
    base_uom_hints = {
        'uom.product_uom_categ_vol': ['L', 'ml', 'Liter', 'Liters'],
        'volume': ['L', 'ml', 'Liter', 'Liters'],
        'volumen': ['L', 'ml', 'Liter', 'Liters'],
    }
    
    hints = base_uom_hints.get(category_hint.lower() if category_hint else '', ['L', 'ml'])
    base_uom = find_base_uom(env, hints)
    
    if not base_uom:
        print(f"  WARNING: No base UoM found for {name}, trying any existing UoM")
        base_uom = env['uom.uom'].search([], limit=1)
        if not base_uom:
            print(f"  ERROR: No UoM available at all, skipping {name}")
            return False

    # Parse factor - in Odoo 19, factor is the conversion rate to the base UoM
    # For Pinta: 1 Pinta = 0.473 L, so factor = 0.473
    try:
        # The CSV has factor_inv which was 1/factor in older Odoo versions
        # In Odoo 19, we use factor directly
        factor_inv = float(row.get('factor_inv', '1') or '1')
        factor = 1.0 / factor_inv if factor_inv != 0 else 1.0
    except ValueError:
        factor = 1.0

    try:
        rounding = float(row.get('rounding', '0.01') or '0.01')
    except ValueError:
        rounding = 0.01

    # Create the UoM with Odoo 19 structure
    vals = {
        'name': name,
        'relative_uom_id': base_uom.id,
        'factor': factor,
        'rounding': rounding,
        'active': True,
    }

    try:
        uom = env['uom.uom'].create(vals)
        print(f"  Created UoM: {name} (id={uom.id}, factor={factor:.3f}, base={base_uom.name})")
        return uom.id
    except Exception as e:
        print(f"  ERROR creating UoM {name}: {e}")
        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================

print("=" * 60)
print("  Pizzeria El Gordo - Initial Setup (UoM Import)")
print("=" * 60)

print("\n[1/2] Checking/Installing required modules...")
# Check if uom module is available
uom_module = env['ir.module.module'].search([('name', '=', 'uom')], limit=1)
if uom_module and uom_module.state == 'installed':
    print("  Module uom is installed")
else:
    print("  Installing uom module...")
    if uom_module:
        uom_module.button_immediate_install()
        env.cr.commit()

# Check stock module
stock_module = env['ir.module.module'].search([('name', '=', 'stock')], limit=1)
if stock_module and stock_module.state == 'installed':
    print("  Module stock is installed")
else:
    print("  Installing stock module...")
    if stock_module:
        stock_module.button_immediate_install()
        env.cr.commit()

# Check mrp module  
mrp_module = env['ir.module.module'].search([('name', '=', 'mrp')], limit=1)
if mrp_module and mrp_module.state == 'installed':
    print("  Module mrp is installed")
else:
    print("  Installing mrp module...")
    if mrp_module:
        mrp_module.button_immediate_install()
        env.cr.commit()

# Check point_of_sale module
pos_module = env['ir.module.module'].search([('name', '=', 'point_of_sale')], limit=1)
if pos_module and pos_module.state == 'installed':
    print("  Module point_of_sale is installed")
else:
    print("  Installing point_of_sale module...")
    if pos_module:
        pos_module.button_immediate_install()
        env.cr.commit()

print("\n[2/2] Creating Units of Measure from CSV...")
uom_rows = csv_rows('unidades.csv')
created_uoms = {}

for row in uom_rows:
    uom_id = create_uom_from_csv(env, row)
    if uom_id:
        created_uoms[row['id']] = uom_id

# Also try the smaller UoM file if it exists
try:
    uom_smaller_rows = csv_rows('unidades-smaller.csv')
    for row in uom_smaller_rows:
        if row['id'] not in created_uoms:
            uom_id = create_uom_from_csv(env, row)
            if uom_id:
                created_uoms[row['id']] = uom_id
except Exception as e:
    print(f"  Note: unidades-smaller.csv not processed ({e})")

env.cr.commit()

print("\n" + "=" * 60)
print("  Initial setup complete!")
print(f"  UoMs created: {len(created_uoms)}")
print("=" * 60)
print("\n  Next step: Run import_products.py to add categories and products")
print("=" * 60)
