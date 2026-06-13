exec(open('/mnt/extra-addons/import_lib.py').read())

print("=" * 60)
print("  [4/5] Creating Bill of Materials...")
print("=" * 60)

product_ids, product_by_name = load_product_index(env)

# ===========================================================================
# A. Ingredient BoMs (Bollo + pizza recipes from receta CSVs)
# ===========================================================================
print("\n  Ingredient BoMs from receta CSVs...")

bollo_bom_rows = csv_rows('receta_del_bollo.csv')
pizza_bom_rows = csv_rows('receta_pizzas_con_masa.csv')
all_bom_rows = bollo_bom_rows + pizza_bom_rows

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
skipped_boms = []
for external_id, bom_data in bom_groups.items():
    tmpl_id = product_ids.get(external_id)
    if not tmpl_id:
        prod_by_name = env['product.template'].search([('default_code', 'ilike', external_id)], limit=1)
        if prod_by_name:
            tmpl_id = prod_by_name.id
    if not tmpl_id:
        print(f"    WARNING: Product not found for BoM: {external_id}")
        skipped_boms.append(external_id)
        continue

    existing_bom = env['mrp.bom'].search([
        ('product_tmpl_id', '=', tmpl_id),
        ('type', '=', bom_data['type']),
    ], limit=1)
    if existing_bom:
        print(f"    BoM exists: {external_id} ({len(existing_bom.bom_line_ids)} lines)")
        bom_count += 1
        continue

    line_vals = []
    for line in bom_data['lines']:
        line_product_id = find_product_by_name(env, line['product_name'])
        if not line_product_id:
            print(f"      WARNING: Ingredient not found: {line['product_name']}")
            continue
        product_product = env['product.product'].search([
            ('product_tmpl_id', '=', line_product_id)
        ], limit=1)
        if not product_product:
            print(f"      WARNING: No product.product for: {line['product_name']}")
            continue
        line_vals.append((0, 0, {
            'product_id': product_product.id,
            'product_qty': line['product_qty'],
            'product_uom_id': product_product.uom_id.id,
        }))

    if not line_vals:
        print(f"    WARNING: No valid lines for BoM: {external_id}, skipping")
        continue

    bom_vals = {
        'product_tmpl_id': tmpl_id,
        'type': bom_data['type'],
        'code': bom_data.get('code', ''),
        'bom_line_ids': line_vals,
    }
    bom = env['mrp.bom'].create(bom_vals)
    bom_count += 1
    print(f"    Created BoM: {external_id} ({len(line_vals)} lines)")

env.cr.commit()
if skipped_boms:
    print(f"\n  SKIPPED {len(skipped_boms)} BoMs (product not found):")
    for s in skipped_boms:
        print(f"    - {s}")

# ===========================================================================
# B. Salon [S] BoMs: copy Mostrador ingredient recipe
#    [S] Mozzarella gets SAME recipe as Mozzarella (Bollo + Muzzarella + Salsa...)
#    NOT a 1x link to Mozzarella (which causes double stock deduction)
#    Always delete any existing salon BoMs first (could be buggy from old import)
# ===========================================================================
print("\n  Salon [S] ingredient BoMs (copying Mostrador recipes)...")

salon_link_count = 0
salon_fixed_count = 0


def create_salon_recipe(env, salon_name, mostrador_name, product_by_name):
    global salon_link_count, salon_fixed_count
    salon_tmpl_id = product_by_name.get(salon_name)
    if not salon_tmpl_id:
        print(f"    WARNING: Salon variant not found: {salon_name}")
        return
    mostrador_tmpl_id = product_by_name.get(mostrador_name)
    if not mostrador_tmpl_id:
        print(f"    WARNING: Mostrador product not found: {mostrador_name}")
        return

    mostrador_bom = env['mrp.bom'].search([
        ('product_tmpl_id', '=', mostrador_tmpl_id),
        ('type', '=', 'phantom'),
    ], limit=1)
    if not mostrador_bom:
        print(f"    WARNING: No Mostrador BoM found for {mostrador_name}")
        return

    line_vals = []
    for line in mostrador_bom.bom_line_ids:
        line_vals.append((0, 0, {
            'product_id': line.product_id.id,
            'product_qty': line.product_qty,
            'product_uom_id': line.product_uom_id.id,
        }))

    # Delete any existing BoMs for this salon product (all types)
    # Old buggy BoMs with direct links to Mostrador products cause double deduction
    existing_boms = env['mrp.bom'].search([
        ('product_tmpl_id', '=', salon_tmpl_id),
    ])
    if existing_boms:
        print(f"    FIXED Salon BoM for {salon_name} (deleted {len(existing_boms)} old BoM(s))")
        existing_boms.unlink()
        salon_fixed_count += 1

    env['mrp.bom'].create({
        'product_tmpl_id': salon_tmpl_id,
        'type': 'phantom',
        'code': f'Salon {mostrador_name}',
        'bom_line_ids': line_vals,
    })
    salon_link_count += 1
    print(f"    Salon recipe: {salon_name} ({len(line_vals)} ingredients, same as {mostrador_name})")


# Pizza salon recipes
salon_pizza_rows = csv_rows('pizzas_salon.csv')
for row in salon_pizza_rows:
    mostrador_name = row['name'].replace('[S] ', '')
    salon_name = row['name']
    create_salon_recipe(env, salon_name, mostrador_name, product_by_name)

# Mitad salon recipes
salon_mitad_rows = csv_rows('mitades_salon.csv')
for row in salon_mitad_rows:
    mostrador_name = row['name'].replace('[S] ', '')
    salon_name = row['name']
    create_salon_recipe(env, salon_name, mostrador_name, product_by_name)

# Empanada salon recipes
salon_emp_rows = csv_rows('empanadas_salon.csv')
for row in salon_emp_rows:
    mostrador_name = row['name'].replace('[S] ', '')
    salon_name = row['name']
    create_salon_recipe(env, salon_name, mostrador_name, product_by_name)

# Panini salon recipes
salon_panini_rows = csv_rows('paninis_salon.csv')
for row in salon_panini_rows:
    mostrador_name = row['name'].replace('[S] ', '')
    salon_name = row['name']
    create_salon_recipe(env, salon_name, mostrador_name, product_by_name)

# Empanada ½ Docena salon recipes
salon_mdoc_emp_rows = csv_rows('empanadas_media_docena_salon.csv')
for row in salon_mdoc_emp_rows:
    mostrador_name = row['name'].replace('[S] ', '')
    salon_name = row['name']
    create_salon_recipe(env, salon_name, mostrador_name, product_by_name)

# Empanada Docena salon recipes
salon_doc_emp_rows = csv_rows('empanadas_docena_salon.csv')
for row in salon_doc_emp_rows:
    mostrador_name = row['name'].replace('[S] ', '')
    salon_name = row['name']
    create_salon_recipe(env, salon_name, mostrador_name, product_by_name)

env.cr.commit()

# ===========================================================================
# C. Validate critical BoM chain
# ===========================================================================
print("\n  Validating BoM chain...")

# Validate Bollo de Masa BoM
bollo = env['product.template'].search([('name', '=', 'Bollo de Masa (Pre-pizza)')], limit=1)
if bollo:
    bom = env['mrp.bom'].search([('product_tmpl_id', '=', bollo.id), ('type', '=', 'phantom')], limit=1)
    if bom:
        print(f"    Bollo BoM OK ({len(bom.bom_line_ids)} lines):")
        for line in bom.bom_line_ids:
            print(f"      {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name}")
    else:
        print("    ERROR: No phantom BoM for Bollo de Masa!")
else:
    print("    WARNING: Bollo de Masa product not found")

# Validate Mostrador Mozzarella BoM
muzza = env['product.template'].search([('name', '=', 'Mozzarella')], limit=1)
if muzza:
    bom = env['mrp.bom'].search([('product_tmpl_id', '=', muzza.id), ('type', '=', 'phantom')], limit=1)
    if bom:
        print(f"    Mozzarella BoM OK ({len(bom.bom_line_ids)} lines):")
        for line in bom.bom_line_ids:
            print(f"      {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name}")
    else:
        print("    ERROR: No phantom BoM for Mozzarella!")

# Validate ALL salon products (check for double-deduction links to Mostrador products)
print("\n  Validating ALL salon BoMs for double-deduction links...")
salon_errors = 0
salon_ok = 0
salon_missing = 0

salon_csv_files = ['pizzas_salon.csv', 'mitades_salon.csv', 'empanadas_salon.csv', 'paninis_salon.csv', 'empanadas_media_docena_salon.csv', 'empanadas_docena_salon.csv']
for csv_file in salon_csv_files:
    salon_rows = csv_rows(csv_file)
    for row in salon_rows:
        salon_name = row['name']
        mostrador_name = salon_name.replace('[S] ', '')

        s_product = env['product.template'].search([('name', '=', salon_name)], limit=1)
        if not s_product:
            salon_missing += 1
            continue

        s_bom = env['mrp.bom'].search([
            ('product_tmpl_id', '=', s_product.id),
            ('type', '=', 'phantom'),
        ], limit=1)
        if not s_bom:
            print(f"    WARNING: No phantom BoM for {salon_name}")
            salon_missing += 1
            continue

        # Check if any BoM line links to the Mostrador product (causes double deduction)
        m_product = env['product.template'].search([('name', '=', mostrador_name)], limit=1)
        has_link_to_mostrador = False
        if m_product:
            has_link_to_mostrador = any(
                line.product_id.product_tmpl_id.id == m_product.id
                for line in s_bom.bom_line_ids
            )

        if has_link_to_mostrador:
            print(f"    ERROR: {salon_name} BoM links to Mostrador {mostrador_name} (causes double deduction!)")
            salon_errors += 1
        else:
            salon_ok += 1

if salon_errors > 0:
    print(f"\n  *** {salon_errors} SALON BOM(S) HAVE DOUBLE-DEDUCTION LINKS! ***")
    print(f"  *** Re-run the import to fix them. ***")
print(f"  Salon BoMs OK: {salon_ok}")
if salon_missing > 0:
    print(f"  Salon BoMs missing: {salon_missing}")

total_boms = env['mrp.bom'].search_count([('type', '=', 'phantom')])
print(f"\n  Total phantom BoMs: {total_boms}")
print(f"  Ingredient BoMs created: {bom_count}")
print(f"  Salon recipes created: {salon_link_count}")
print(f"  Salon BoMs fixed (replaced): {salon_fixed_count}")