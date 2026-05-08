#!/usr/bin/env python3
print("=" * 70)
print("  Checking Bollo de Masa BoM")
print("=" * 70)

bollo = env['product.template'].search([('name', '=', 'Bollo de Masa (Pre-pizza)')], limit=1)
if bollo:
    print(f'Product: {bollo.name} (ID: {bollo.id})')
    print(f'Type: {bollo.type}')
    
    bom = env['mrp.bom'].search([('product_tmpl_id', '=', bollo.id), ('type', '=', 'phantom')], limit=1)
    if bom:
        print(f'\nPhantom BoM: {bom.code or bom.id}')
        print(f'BoM lines ({len(bom.bom_line_ids)}):')
        for line in bom.bom_line_ids:
            print(f'  - {line.product_id.display_name}: {line.product_qty} {line.product_uom_id.name}')
            print(f'    Product ID: {line.product_id.id}, Template: {line.product_id.product_tmpl_id.name}')
    else:
        print('\nNo phantom BoM found for Bollo!')
        
    # Check if Harina exists
    print('\nChecking Harina product...')
    harina = env['product.template'].search([('name', '=', 'Harina 0000')], limit=1)
    if harina:
        print(f'Harina found: {harina.name} (ID: {harina.id})')
        harina_v = env['product.product'].search([('product_tmpl_id', '=', harina.id)], limit=1)
        if harina_v:
            print(f'Harina variant: {harina_v.id}')
            # Check if this variant is in any BoM lines
            in_bom = env['mrp.bom.line'].search([('product_id', '=', harina_v.id)])
            print(f'Harina appears in {len(in_bom)} BoM lines')
            for bl in in_bom:
                print(f'  - BoM: {bl.bom_id.product_tmpl_id.name if bl.bom_id else "N/A"}')
    else:
        print('Harina 0000 NOT found!')
else:
    print('Bollo de Masa product not found!')

print("=" * 70)