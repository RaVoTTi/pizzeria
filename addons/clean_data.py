print("=" * 60)
print("  Pizzeria El Gordo - Cleaning imported data")
print("=" * 60)

# ── 1. Close and delete POS sessions ──────────────────────
print("\n[1/10] Closing and deleting POS sessions...")
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

orders = env['pos.order'].search([])
n_orders = len(orders)
orders.unlink()
env.cr.commit()
print(f"  Deleted {n_orders} POS orders")

# ── 2. Delete restaurant tables and floors ─────────────────
print("\n[2/10] Deleting restaurant tables and floors...")
tables = env['restaurant.table'].search([])
n_tables = len(tables)
tables.unlink()
env.cr.commit()
print(f"  Deleted {n_tables} tables")

floors = env['restaurant.floor'].search([])
n_floors = len(floors)
floors.unlink()
env.cr.commit()
print(f"  Deleted {n_floors} floors")

# ── 3. Raw SQL: wipe stock, sale, and accounting records ──
#     ORM blocks deletion of "done" state records, so we use
#     raw SQL to bypass those protections. Order matters for FKs.
print("\n[3/10] Wiping stock, sale, and accounting records (raw SQL)...")
tables_wiped = [
    ('pos_payment', 'pos payment records'),
    ('pos_order_line', 'pos order lines'),
    ('account_move_line', 'journal item lines'),
    ('account_move', 'journal entries (out invoices/receipts)'),
    ('sale_order_line', 'sale order lines'),
    ('sale_order', 'sale orders'),
    ('stock_move_line', 'stock move lines'),
    ('stock_move', 'stock moves'),
    ('stock_picking', 'stock pickings'),
    ('stock_quant', 'stock quants'),
]
for table, label in tables_wiped:
    if table == 'account_move':
        env.cr.execute(f"DELETE FROM {table} WHERE move_type IN ('out_invoice', 'out_receipt', 'entry')")
    elif table == 'account_move_line':
        env.cr.execute(f"DELETE FROM {table} WHERE move_id IN (SELECT id FROM account_move WHERE move_type IN ('out_invoice', 'out_receipt', 'entry'))")
    else:
        env.cr.execute(f"DELETE FROM {table}")
    count = env.cr.rowcount
    print(f"  {label}: {count} rows")

env.cr.commit()

# ── 4. Delete Bills of Materials ──────────────────────────
print("\n[4/10] Deleting Bills of Materials...")
boms = env['mrp.bom'].search([])
n_boms = len(boms)
boms.unlink()
env.cr.commit()
print(f"  Deleted {n_boms} BoMs")

# ── 5. Delete POS categories ──────────────────────────────
print("\n[5/10] Deleting POS categories...")
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

# ── 6. Delete products under our category tree ────────────
print("\n[6/10] Deleting products...")
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

# ── 7. Delete custom product categories ───────────────────
print("\n[7/10] Deleting custom product categories...")
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

# ── 8. Delete payment methods and journals we created ─────
print("\n[8/10] Deleting payment methods and journals...")
for pm_name in ['Mercado Pago Terminal', 'Efectivo', 'Cash']:
    pm = env['pos.payment.method'].search([('name', '=', pm_name)])
    if pm:
        pm.unlink()
        env.cr.commit()
        print(f"  Deleted payment method(s): {pm_name}")

for journal_code in ['MPAGO', 'CASH']:
    journal = env['account.journal'].search([('code', '=', journal_code)])
    if journal:
        journal.unlink()
        env.cr.commit()
        print(f"  Deleted journal(s): {journal_code}")

# ── 8b. Delete preparation displays ────────────────────────
print("\n[9/10] Deleting preparation displays...")
try:
    displays = env['pos_preparation_display.display'].search([])
    if displays:
        n = len(displays)
        displays.unlink()
        env.cr.commit()
        print(f"  Deleted {n} preparation display(s)")
    else:
        print("  No preparation displays found")
except KeyError:
    print("  Module pos_preparation_display not installed — skipping")

# ── 10. Delete custom UoMs ────────────────────────────────
print("\n[10/10] Deleting custom UoMs...")
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