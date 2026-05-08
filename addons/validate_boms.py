print("=" * 60)
print("  BoM & Product Validation Diagnostic")
print("=" * 60)

errors = 0

# 1. Check Bollo de Masa product
bollo = env['product.template'].search([('name', '=', 'Bollo de Masa (Pre-pizza)')], limit=1)
if not bollo:
    print("  ERROR: Bollo de Masa product NOT FOUND!")
    errors += 1
else:
    print(f"\n  Bollo de Masa: id={bollo.id}, type={bollo.type}, storable={bollo.is_storable}")
    if not bollo.is_storable:
        print(f"    ERROR: Bollo must be storable for phantom BoM to work!")
        errors += 1
    if bollo.type != 'consu':
        print(f"    WARNING: Bollo type is '{bollo.type}', expected 'consu'")

    bom = env['mrp.bom'].search([('product_tmpl_id', '=', bollo.id), ('type', '=', 'phantom')], limit=1)
    if not bom:
        print("    ERROR: No phantom BoM for Bollo!")
        errors += 1
    else:
        print(f"    BoM: {len(bom.bom_line_ids)} lines")
        for line in bom.bom_line_ids:
            pp = line.product_id
            storable = "OK" if pp.is_storable else "NOT STORABLE!"
            print(f"      {pp.display_name}: {line.product_qty} {line.product_uom_id.name} [{storable}]")
            if not pp.is_storable:
                errors += 1

# 2. Check key ingredients are storable
print("\n  Checking ingredient storable status...")
ingredient_names = ['Harina 0000', 'Agua Filtrada', 'Levadura Fresca',
                    'Muzzarella Cilindro', 'Salsa de Tomate Base']
for name in ingredient_names:
    prod = env['product.template'].search([('name', '=', name)], limit=1)
    if not prod:
        print(f"    ERROR: {name} NOT FOUND!")
        errors += 1
    elif not prod.is_storable:
        print(f"    ERROR: {name} type={prod.type} storable={prod.is_storable} (MUST be storable)")
        errors += 1
    else:
        print(f"    OK: {name} type={prod.type} storable={prod.is_storable}")

# 3. Check a pizza BoM chain (Mozzarella)
print("\n  Checking Mozzarella BoM chain...")
muzza = env['product.template'].search([('name', '=', 'Mozzarella')], limit=1)
if not muzza:
    print("    ERROR: Mozzarella product NOT FOUND!")
    errors += 1
else:
    print(f"    Mozzarella: id={muzza.id}, type={muzza.type}, storable={muzza.is_storable}")
    bom = env['mrp.bom'].search([('product_tmpl_id', '=', muzza.id), ('type', '=', 'phantom')], limit=1)
    if not bom:
        print("    ERROR: No phantom BoM for Mozzarella!")
        errors += 1
    else:
        print(f"    BoM: {len(bom.bom_line_ids)} lines")
        for line in bom.bom_line_ids:
            pp = line.product_id
            print(f"      {pp.display_name}: {line.product_qty} {line.product_uom_id.name}")

# 4. Check [S] Mozzarella BoM chain
print("\n  Checking [S] Mozzarella BoM chain...")
s_muzza = env['product.template'].search([('name', '=', '[S] Mozzarella')], limit=1)
if not s_muzza:
    print("    WARNING: [S] Mozzarella product NOT FOUND")
else:
    bom = env['mrp.bom'].search([('product_tmpl_id', '=', s_muzza.id), ('type', '=', 'phantom')], limit=1)
    if not bom:
        print("    ERROR: No phantom BoM for [S] Mozzarella!")
        errors += 1
    else:
        print(f"    BoM: {len(bom.bom_line_ids)} lines")
        for line in bom.bom_line_ids:
            pp = line.product_id
            print(f"      {pp.display_name}: {line.product_qty} {line.product_uom_id.name}")
        if len(bom.bom_line_ids) != 1:
            print(f"    ERROR: [S] Mozzarella BoM should have 1 line (Mostrador), has {len(bom.bom_line_ids)}!")
            errors += 1
        else:
            link_name = bom.bom_line_ids[0].product_id.display_name
            link_qty = bom.bom_line_ids[0].product_qty
            print(f"    OK: [S] Mozzarella -> {link_qty}x {link_name}")

# 5. Check for duplicate BoMs
print("\n  Checking for duplicate BoMs...")
all_boms = env['mrp.bom'].search([('type', '=', 'phantom')])
seen = {}
for bom in all_boms:
    key = bom.product_tmpl_id.id
    if key in seen:
        print(f"    DUPLICATE: {bom.product_tmpl_id.name} has multiple phantom BoMs!")
        errors += 1
    seen[key] = seen.get(key, 0) + 1

# 6. Count phantom BoMs
phantom_count = env['mrp.bom'].search_count([('type', '=', 'phantom')])
print(f"\n  Total phantom BoMs: {phantom_count}")

# 7. Verify expected BoM count
expected_pizzas = env['product.template'].search_count([('name', 'not like', '[S]%'), ('categ_id.name', '=', 'Pizzas')])
expected_mitades = env['product.template'].search_count([('name', 'not like', '[S]%'), ('categ_id.name', '=', 'Mitades')])
expected_salon = env['product.template'].search_count([('name', 'like', '[S]%')])
bollo_bom = 1 if bollo else 0
expected_boms = expected_pizzas + expected_mitades + expected_salon + bollo_bom
print(f"  Expected BoMs: {expected_pizzas} pizzas + {expected_mitades} mitades + {expected_salon} [S] links + {bollo_bom} bollo = {expected_boms}")
if phantom_count != expected_boms:
    print(f"  WARNING: Expected {expected_boms} phantom BoMs, got {phantom_count}")

# 8. Simulate stock deduction for 1 Mozzarella
print("\n  Simulating stock deduction for 1x Mozzarella:")
if muzza:
    bom = env['mrp.bom'].search([('product_tmpl_id', '=', muzza.id), ('type', '=', 'phantom')], limit=1)
    if bom:
        def explode_bom(product_tmpl_id, qty, depth=0):
            prefix = "    " * (depth + 1)
            bom = env['mrp.bom'].search([('product_tmpl_id', '=', product_tmpl_id), ('type', '=', 'phantom')], limit=1)
            if not bom:
                prod = env['product.template'].browse(product_tmpl_id)
                print(f"{prefix}{prod.name}: {qty}")
                return
            for line in bom.bom_line_ids:
                line_qty = line.product_qty * qty
                explode_bom(line.product_id.product_tmpl_id.id, line_qty, depth + 1)

        print(f"  Mozzarella (qty 1):")
        explode_bom(muzza.id, 1)

print(f"\n{'=' * 60}")
if errors == 0:
    print("  ALL CHECKS PASSED")
else:
    print(f"  {errors} ERROR(S) FOUND - see above")
print("=" * 60)