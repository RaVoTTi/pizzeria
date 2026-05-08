print("=" * 60)
print("  Pizzeria El Gordo - Cleaning imported data")
print("=" * 60)

# ── 1. Close and delete POS sessions ──────────────────────
print("\n[1/9] Closing and deleting POS sessions...")
sessions = env['pos.session'].search([])
for s in sessions:
    if s.state != 'closed':
        try:
            s.action_pos_session_closing_control()
            s.action_pos_session_close()
        except Exception:
            pass
n_sessions = len(sessions)
sessions.unlink()
env.cr.commit()
print(f"  Deleted {n_sessions} POS sessions")

# POS orders
orders = env['pos.order'].search([])
n_orders = len(orders)
orders.unlink()
env.cr.commit()
print(f"  Deleted {n_orders} POS orders")

# ── 2. Delete restaurant tables ────────────────────────────
print("\n[2/9] Deleting restaurant tables...")
tables = env['restaurant.table'].search([])
n_tables = len(tables)
tables.unlink()
env.cr.commit()
print(f"  Deleted {n_tables} tables")

# ── 3. Delete restaurant floors ────────────────────────────
print("\n[3/9] Deleting restaurant floors...")
floors = env['restaurant.floor'].search([])
n_floors = len(floors)
floors.unlink()
env.cr.commit()
print(f"  Deleted {n_floors} floors")

# ── 4. Delete stock quants (inventory adjustments) ─────────
print("\n[4/9] Deleting stock quants...")
quants = env['stock.quant'].search([])
n_quants = len(quants)
quants.unlink()
env.cr.commit()
print(f"  Deleted {n_quants} stock quants")

# ── 5. Delete Bills of Materials ───────────────────────────
print("\n[5/9] Deleting Bills of Materials...")
boms = env['mrp.bom'].search([])
n_boms = len(boms)
boms.unlink()
env.cr.commit()
print(f"  Deleted {n_boms} BoMs")

# ── 6. Delete POS categories ───────────────────────────────
print("\n[6/9] Deleting POS categories...")
POS_CAT_NAMES = [
    'Empanadas', '[S] Empanadas', 'Pizzas', '[S] Pizzas',
    'Mitades', '[S] Mitades', 'Cerveza', 'Bebidas', 'Delivery',
]
for name in POS_CAT_NAMES:
    cats = env['pos.category'].search([('name', '=', name)])
    if cats:
        n = len(cats)
        cats.unlink()
        print(f"  Deleted pos.category: {name} ({n})")
    else:
        print(f"  Not found: {name}")
env.cr.commit()

# ── 7. Delete products under our category tree ─────────────
print("\n[7/9] Deleting products...")
todos_cat = env['product.category'].search([('name', '=', 'Todos')], limit=1)
if todos_cat:
    child_cats = env['product.category'].search([('id', 'child_of', todos_cat.id)])
    cat_ids = child_cats.ids
    products = env['product.template'].search([('categ_id', 'in', cat_ids)])
    n_prods = len(products)
    products.unlink()
    env.cr.commit()
    print(f"  Deleted {n_prods} products in our categories")
else:
    print("  WARNING: 'Todos' category not found, nothing deleted")

# ── 8. Delete custom product categories ────────────────────
print("\n[8/9] Deleting custom product categories...")
if todos_cat:
    cats = env['product.category'].search(
        [('id', 'child_of', todos_cat.id)],
        order='parent_path desc'
    )
    n_cats = len(cats)
    cats.unlink()
    env.cr.commit()
    print(f"  Deleted {n_cats} categories")
else:
    print("  Nothing to delete")

# ── 9. Delete custom UoMs ──────────────────────────────────
print("\n[9/9] Deleting custom UoMs...")
pinta = env['uom.uom'].search([('name', '=', 'Pinta')])
if pinta:
    pinta.unlink()
    env.cr.commit()
    print("  Deleted UoM: Pinta")
else:
    print("  UoM Pinta not found")

print("\n" + "=" * 60)
print("  Data clean complete — ready for re-import")
print("=" * 60)
