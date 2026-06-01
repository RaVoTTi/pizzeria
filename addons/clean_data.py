print("=" * 60)
print("  Pizzeria El Gordo - Cleaning imported data")
print("=" * 60)


def safe_unlink(model_name, domain=None, label=None):
    """Search and unlink records, skip if model not installed."""
    label = label or model_name
    if model_name not in env:
        print(f"  {label} — model not installed, skipping")
        return 0
    records = env[model_name].search(domain or [])
    count = len(records)
    if count:
        records.unlink()
        env.cr.commit()
    print(f"  Deleted {count} {label}")
    return count


def safe_sql(sql, label=""):
    """Execute raw SQL, ignore errors."""
    try:
        env.cr.execute(sql)
        env.cr.commit()
        if label:
            print(f"  {label}: {env.cr.rowcount} rows")
    except Exception as e:
        env.cr.rollback()
        if label:
            print(f"  {label} — skipped: {e}")


# ── 0. Ensure required modules are installed ──────────────
print("\n[0/12] Checking required modules...")
for mod_name in ['pos_kitchen_screen_odoo', 'pos_receipt_logo']:
    mod = env['ir.module.module'].search([('name', '=', mod_name)], limit=1)
    if mod and mod.state != 'installed':
        print(f"  WARNING: {mod_name} is {mod.state}, needs install via CLI first:")
        print(f"    docker compose run --rm web odoo -c /etc/odoo/odoo.conf -d elgordo -i {mod_name} --stop-after-init")
    elif mod:
        print(f"  {mod_name} installed")
    else:
        print(f"  WARNING: Module {mod_name} not found")

# ── 1. Kitchen tickets ────────────────────────────────────
print("\n[1/12] Deleting kitchen tickets...")
if 'pos.kitchen.ticket.line' in env:
    env['pos.kitchen.ticket.line'].search([]).unlink()
    env.cr.commit()
    safe_unlink('pos.kitchen.ticket', label="kitchen tickets")
else:
    print("  pos_kitchen_screen_odoo not installed — skipping")

# ── 2. Close and delete POS sessions ──────────────────────
print("\n[2/12] Closing and deleting POS sessions...")
sessions = env['pos.session'].search([])
for s in sessions:
    if s.state != 'closed':
        try:
            s.action_pos_session_closing_control()
        except Exception:
            pass
        try:
            s.action_pos_session_close()
        except Exception:
            pass
n_sessions = len(sessions)
sessions.unlink()
env.cr.commit()
print(f"  Deleted {n_sessions} POS sessions")

# ── 3. Cancel and delete POS orders ──────────────────────
print("\n[3/12] Cancelling and deleting POS orders...")
orders = env['pos.order'].search([])
for order in orders:
    if order.state in ('paid', 'done', 'invoiced'):
        try:
            order.with_context(force_delete=True).unlink()
        except Exception:
            try:
                order._cr.execute("UPDATE pos_order SET state='cancel' WHERE id=%s", (order.id,))
                order._cr.commit()
                order.invalidate_cache()
            except Exception:
                pass
remaining = env['pos.order'].search([])
remaining.unlink()
env.cr.commit()
print(f"  Deleted {len(orders)} POS orders")

# ── 4. Delete restaurant tables and floors ─────────────────
print("\n[4/12] Deleting restaurant tables and floors...")
safe_unlink('restaurant.table', label="tables")
safe_unlink('restaurant.floor', label="floors")

# ── 5. Delete POS config ──────────────────────────────────
print("\n[5/12] Deleting POS configs...")
if 'pos.config' in env:
    configs = env['pos.config'].search([])
    for config in configs:
        config_sessions = env['pos.session'].search([('config_id', '=', config.id)])
        for s in config_sessions:
            if s.state != 'closed':
                try:
                    s.action_pos_session_closing_control()
                except Exception:
                    pass
                try:
                    s.action_pos_session_close()
                except Exception:
                    pass
    n_configs = len(configs)
    configs.unlink()
    env.cr.commit()
    print(f"  Deleted {n_configs} POS configs")
else:
    print("  pos module not installed — skipping")

# ── 6. Delete accounting records ─────────────────────────
print("\n[6/12] Deleting accounting records...")
safe_sql("DELETE FROM account_partial_reconcile", "Reconciliations")
safe_sql(
    "DELETE FROM account_move_line WHERE move_id IN "
    "(SELECT id FROM account_move WHERE move_type IN ('out_invoice','out_receipt','entry'))",
    "Journal item lines",
)
safe_sql(
    "DELETE FROM account_move WHERE move_type IN ('out_invoice','out_receipt','entry')",
    "Journal entries",
)

# ── 7. Delete stock records ────────────────────────────────
print("\n[7/12] Deleting stock records...")
if 'stock.picking' in env:
    for p in env['stock.picking'].search([('state', 'not in', ('done', 'cancel'))]):
        try:
            p._action_cancel()
        except Exception:
            pass
    env.cr.commit()
safe_sql("DELETE FROM stock_move_line", "Stock move lines")
safe_sql("DELETE FROM stock_move", "Stock moves")
safe_sql("DELETE FROM stock_picking", "Pickings")
safe_sql("DELETE FROM stock_quant", "Quants")

# ── 7b. Delete sale orders (reference products) ───────────
print("\n[7b/12] Deleting sale orders...")
safe_sql("DELETE FROM sale_order_line", "Sale order lines")
safe_sql("DELETE FROM sale_order", "Sale orders")

# ── 8. Delete Bills of Materials ──────────────────────────
print("\n[8/12] Deleting Bills of Materials...")
if 'mrp.bom' in env:
    safe_unlink('mrp.bom', label="BoMs")
else:
    # Try direct SQL as fallback
    safe_sql("DELETE FROM mrp_bom", "BoMs (SQL)")
    safe_sql("DELETE FROM mrp_bom_line", "BoM lines (SQL)")

# ── 9. Delete POS categories ──────────────────────────────
print("\n[9/12] Deleting POS categories...")
POS_CAT_NAMES = [
    'Empanadas', '[S] Empanadas', 'Pizzas', '[S] Pizzas',
    'Mitades', '[S] Mitades', 'Cerveza', 'Bebidas', 'Delivery',
]
for name in POS_CAT_NAMES:
    cats = env['pos.category'].search([('name', '=', name)])
    if cats:
        cats.unlink()
        print(f"  Deleted pos.category: {name} ({len(cats)})")
    else:
        print(f"  Not found: {name}")
env.cr.commit()

# ── 10. Delete products under our category tree ────────────
print("\n[10/12] Deleting products...")
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
    print("  'Todos' category not found, nothing deleted")

# ── 10b. Delete custom product categories ───────────────────
print("\n[10b/12] Deleting custom product categories...")
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

# ── 10c. Delete payment methods, journals, preparation displays ─
print("\n[10c/12] Deleting payment methods and journals...")
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

safe_unlink('pos_preparation_display.display', label="preparation displays")

# ── 11. Delete custom UoMs ────────────────────────────────
print("\n[11/12] Deleting custom UoMs...")
pinta = env['uom.uom'].search([('name', '=', 'Pinta')])
if pinta:
    pinta.unlink()
    env.cr.commit()
    print("  Deleted UoM: Pinta")
else:
    print("  UoM Pinta not found")

# ── 12. Delete kitchen screen config ──────────────────────
print("\n[12/12] Deleting kitchen screen config...")
if 'kitchen.screen' in env:
    screens = env['kitchen.screen'].search([])
    n_screens = len(screens)
    screens.unlink()
    env.cr.commit()
    print(f"  Deleted {n_screens} kitchen screen(s)")
else:
    print("  kitchen.screen not installed — skipping")

print("\n" + "=" * 60)
print("  Data clean complete — ready for re-import")
print("=" * 60)