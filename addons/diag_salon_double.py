print("=" * 60)
print("  [S] Salon Double-Deduction Diagnostic")
print("=" * 60)

# Find [S] Mozzarella
s_muzza = env['product.template'].search([('name', '=', '[S] Mozzarella')], limit=1)
if not s_muzza:
    print("  ERROR: [S] Mozzarella not found!")
else:
    print(f"\n  [S] Mozzarella: id={s_muzza.id}, type={s_muzza.type}, storable={s_muzza.is_storable}, uom={s_muzza.uom_id.name}")

    all_boms = env['mrp.bom'].search([('product_tmpl_id', '=', s_muzza.id)])
    print(f"  ALL BoMs for [S] Mozzarella: {len(all_boms)}")
    for bom in all_boms:
        print(f"    BoM id={bom.id}, type={bom.type}, code={bom.code}")
        for line in bom.bom_line_ids:
            pp = line.product_id
            pt = pp.product_tmpl_id
            print(f"      LINE: {pp.display_name} (product_tmpl={pt.name})")
            print(f"        product_qty={line.product_qty}, product_uom_id={line.product_uom_id.name}")
            print(f"        product_id={pp.id}, is_storable={pt.is_storable}, pt.type={pt.type}, pt.uom={pt.uom_id.name}")

    # Trace the full BoM explosion manually
    print(f"\n  --- Manual BoM explosion for 1x [S] Mozzarella ---")
    def trace_bom(product_name, qty, depth=0):
        prefix = "    " * depth
        pt = env['product.template'].search([('name', '=', product_name)], limit=1)
        if not pt:
            print(f"{prefix}NOT FOUND: {product_name}")
            return
        bom = env['mrp.bom'].search([('product_tmpl_id', '=', pt.id), ('type', '=', 'phantom')], limit=1)
        if not bom:
            print(f"{prefix}{product_name}: {qty} (leaf ingredient)")
            return
        print(f"{prefix}{product_name}: {qty} (phantom BoM with {len(bom.bom_line_ids)} lines)")
        for line in bom.bom_line_ids:
            child_name = line.product_id.product_tmpl_id.name
            child_qty = line.product_qty * qty
            print(f"{prefix}  -> line: product_qty={line.product_qty}, uom={line.product_uom_id.name}, child={child_name}")
            trace_bom(child_name, child_qty, depth + 1)

    trace_bom('[S] Mozzarella', 1)

# Find Mostrador Mozzarella
muzza = env['product.template'].search([('name', '=', 'Mozzarella')], limit=1)
if muzza:
    print(f"\n  Mostrador Mozzarella: id={muzza.id}, type={muzza.type}, storable={muzza.is_storable}, uom={muzza.uom_id.name}")
    all_boms = env['mrp.bom'].search([('product_tmpl_id', '=', muzza.id)])
    print(f"  ALL BoMs for Mozzarella: {len(all_boms)}")
    for bom in all_boms:
        print(f"    BoM id={bom.id}, type={bom.type}, code={bom.code}")
        for line in bom.bom_line_ids:
            pp = line.product_id
            print(f"      LINE: {pp.display_name}, qty={line.product_qty}, uom={line.product_uom_id.name}")

# Find Bollo
bollo = env['product.template'].search([('name', '=', 'Bollo de Masa (Pre-pizza)')], limit=1)
if bollo:
    print(f"\n  Bollo de Masa: id={bollo.id}, type={bollo.type}, storable={bollo.is_storable}, uom={bollo.uom_id.name}")
    all_boms = env['mrp.bom'].search([('product_tmpl_id', '=', bollo.id)])
    print(f"  ALL BoMs for Bollo: {len(all_boms)}")
    for bom in all_boms:
        print(f"    BoM id={bom.id}, type={bom.type}, code={bom.code}")
        for line in bom.bom_line_ids:
            pp = line.product_id
            print(f"      LINE: {pp.display_name}, qty={line.product_qty}, uom={line.product_uom_id.name}")

# Count all phantom BoMs on products with [S] prefix
print(f"\n  --- All [S] products with phantom BoMs ---")
s_products = env['product.template'].search([('name', 'like', '[S]%')])
for sp in s_products:
    boms = env['mrp.bom'].search([('product_tmpl_id', '=', sp.id), ('type', '=', 'phantom')])
    print(f"  {sp.name}: {len(boms)} phantom BoM(s)")
    for bom in boms:
        for line in bom.bom_line_ids:
            print(f"    line: {line.product_id.display_name}, qty={line.product_qty}, uom={line.product_uom_id.name}")

print("\n" + "=" * 60)