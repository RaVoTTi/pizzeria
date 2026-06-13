exec(open('/mnt/extra-addons/import_lib.py').read())

print("=" * 60)
print("  [3/5] Creating saleable products (pizzas, mitades, empanadas, paninis, docenas)...")
print("=" * 60)

cat_ids = load_category_index(env)
product_ids, product_by_name = load_product_index(env)

# --- Pizzas Mostrador ---
print("\n  Pizzas — Mostrador...")
pizza_rows = csv_rows('pizzas.csv')
for row in pizza_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=False)
env.cr.commit()

# --- Pizzas Salon ---
print("\n  Pizzas — Salon...")
salon_pizza_rows = csv_rows('pizzas_salon.csv')
for row in salon_pizza_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=True)
env.cr.commit()

# --- Empanadas Mostrador ---
print("\n  Empanadas — Mostrador...")
emp_rows = csv_rows('empanadas.csv')
for row in emp_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=False)
env.cr.commit()

# --- Empanadas Salon ---
print("\n  Empanadas — Salon...")
salon_emp_rows = csv_rows('empanadas_salon.csv')
for row in salon_emp_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=True)
env.cr.commit()

# --- Empanadas ½ Docena Mostrador ---
print("\n  Empanadas ½ Docena — Mostrador...")
mdoc_emp_rows = csv_rows('empanadas_media_docena.csv')
for row in mdoc_emp_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=False)
env.cr.commit()

# --- Empanadas ½ Docena Salon ---
print("\n  Empanadas ½ Docena — Salon...")
salon_mdoc_emp_rows = csv_rows('empanadas_media_docena_salon.csv')
for row in salon_mdoc_emp_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=True)
env.cr.commit()

# --- Empanadas Docena Mostrador ---
print("\n  Empanadas Docena — Mostrador...")
doc_emp_rows = csv_rows('empanadas_docena.csv')
for row in doc_emp_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=False)
env.cr.commit()

# --- Empanadas Docena Salon ---
print("\n  Empanadas Docena — Salon...")
salon_doc_emp_rows = csv_rows('empanadas_docena_salon.csv')
for row in salon_doc_emp_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=True)
env.cr.commit()

# --- Paninis Mostrador ---
print("\n  Paninis — Mostrador...")
panini_rows = csv_rows('paninis.csv')
for row in panini_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=False)
env.cr.commit()

# --- Paninis Salon ---
print("\n  Paninis — Salon...")
salon_panini_rows = csv_rows('paninis_salon.csv')
for row in salon_panini_rows:
    create_product_from_csv(env, row, cat_ids, product_ids, product_by_name, is_salon=True)
env.cr.commit()

print(f"\n  Mostrador pizzas: {len(pizza_rows)}")
print(f"  Salon pizzas: {len(salon_pizza_rows)}")
print(f"  Mostrador empanadas: {len(emp_rows)}")
print(f"  Salon empanadas: {len(salon_emp_rows)}")
print(f"  Mostrador ½ docena empanadas: {len(mdoc_emp_rows)}")
print(f"  Salon ½ docena empanadas: {len(salon_mdoc_emp_rows)}")
print(f"  Mostrador docena empanadas: {len(doc_emp_rows)}")
print(f"  Salon docena empanadas: {len(salon_doc_emp_rows)}")
print(f"  Mostrador paninis: {len(panini_rows)}")
print(f"  Salon paninis: {len(salon_panini_rows)}")
