print("=" * 60)
print("  Payment Method Setup")
print("=" * 60)

COMPANY_ID = env.company.id

print("\n  Mercado Pago is currently disabled.")
print("  Ensuring POS has a working cash payment method...")

cash_journal = env['account.journal'].search([
    ('type', '=', 'cash'),
    ('company_id', '=', COMPANY_ID),
], limit=1)

if not cash_journal:
    cash_journal = env['account.journal'].create({
        'name': 'Cash',
        'type': 'cash',
        'code': 'CASH',
        'company_id': COMPANY_ID,
    })
    env.cr.commit()
    print(f"  Created cash journal: {cash_journal.name} (id={cash_journal.id})")
else:
    print(f"  Cash journal exists: {cash_journal.name} (id={cash_journal.id})")

existing_pm = env['pos.payment.method'].search([
    ('journal_id', '=', cash_journal.id),
    ('company_id', '=', COMPANY_ID),
], limit=1)

if existing_pm:
    print(f"  Cash payment method already exists: {existing_pm.name} (id={existing_pm.id})")
    payment_method = existing_pm
else:
    payment_method = env['pos.payment.method'].create({
        'name': 'Efectivo',
        'journal_id': cash_journal.id,
        'company_id': COMPANY_ID,
    })
    env.cr.commit()
    print(f"  Created payment method: {payment_method.name} (id={payment_method.id})")

pos_configs = env['pos.config'].search([('company_id', '=', COMPANY_ID)])

if not pos_configs:
    print("  WARNING: No POS configs found. Run the data import first.")
else:
    for pos in pos_configs:
        existing_ids = pos.payment_method_ids.ids
        if payment_method.id in existing_ids:
            print(f"  Already linked to POS: {pos.name} (id={pos.id})")
            continue
        open_sessions = env['pos.session'].search([
            ('config_id', '=', pos.id),
            ('state', 'not in', ['closed', 'closing_control']),
        ])
        if open_sessions:
            print(f"  SKIPPED {pos.name} (id={pos.id}): {len(open_sessions)} open session(s). Close via UI first.")
            continue
        pos.write({'payment_method_ids': [(4, payment_method.id)]})
        env.cr.commit()
        print(f"  Linked to POS: {pos.name} (id={pos.id})")

print("\n" + "=" * 60)
print("  Setup complete!")
print("=" * 60)
print(f"""
  Payment Method: {payment_method.name}
  Linked to:      {len(pos_configs)} POS config(s)

  To enable Mercado Pago later:
  1. Install pos_mercado_pago module
  2. Add MP credentials in Odoo UI
  3. Create a bank journal payment method
""")
print("=" * 60)