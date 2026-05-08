exec(open('/mnt/extra-addons/import_lib.py').read())

print("=" * 60)
print("  [1/5] Creating product categories...")
print("=" * 60)

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
print(f"\n  Categories: {len(cat_ids)}")