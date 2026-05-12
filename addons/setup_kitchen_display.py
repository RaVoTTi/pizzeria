print("=" * 60)
print("  POS Kitchen Screen Setup")
print("=" * 60)

# ── 1. Ensure pos_kitchen_screen_odoo module is installed ──
print("\n[1/4] Ensuring pos_kitchen_screen_odoo module is installed...")
module = env['ir.module.module'].search(
    [('name', '=', 'pos_kitchen_screen_odoo')], limit=1
)
if not module:
    print("  ERROR: pos_kitchen_screen_odoo module not found!")
    print("  Check that custom_addons/ is mounted and addons_path is correct.")
else:
    if module.state != 'installed':
        print(f"  Installing pos_kitchen_screen_odoo (state={module.state})...")
        module.button_immediate_install()
        env.cr.commit()
        print("  Module installed.")
    else:
        print("  Module already installed.")

# ── 2. Assign Kitchen Cook group to admin users ───────────
print("\n[2/4] Assigning Kitchen Cook group to admin users...")
kitchen_group = env['res.groups'].search(
    [('name', 'ilike', 'Kitchen Cook')], limit=1
)
if kitchen_group:
    admin_user = env.ref('base.user_admin', raise_if_not_found=False)
    super_user = env.ref('base.user_root', raise_if_not_found=False)
    for user in [admin_user, super_user]:
        if user and kitchen_group not in user.group_ids:
            user.write({'group_ids': [(4, kitchen_group.id)]})
            print(f"  Added Kitchen Cook to user: {user.login} (id={user.id})")
        elif user:
            print(f"  User {user.login} already has Kitchen Cook group")
    env.cr.commit()
else:
    print("  WARNING: Kitchen Cook group not found")

# ── 3. Find POS categories for the kitchen ─────────────────
print("\n[3/4] Finding kitchen POS categories...")
KITCHEN_CATEGORY_NAMES = [
    'Pizzas', '[S] Pizzas',
    'Mitades', '[S] Mitades',
    'Empanadas', '[S] Empanadas',
]

kitchen_cats = env['pos.category'].search(
    [('name', 'in', KITCHEN_CATEGORY_NAMES)]
)
found_names = list(kitchen_cats.mapped('name'))
print(f"  Found {len(kitchen_cats)} categories: {', '.join(found_names)}")

for name in KITCHEN_CATEGORY_NAMES:
    if name not in found_names:
        print(f"  WARNING: POS category '{name}' not found")

# ── 4. Create or update Kitchen Screen config ─────────────
print("\n[4/4] Setting up Kitchen Screen configuration...")
KitchenScreen = env['kitchen.screen']
pos_configs = env['pos.config'].search([('company_id', '=', env.company.id)])

if not pos_configs:
    print("  WARNING: No POS configs found. Run the data import first.")
else:
    for pos_config in pos_configs:
        existing = KitchenScreen.search(
            [('pos_config_id', '=', pos_config.id)], limit=1
        )
        vals = {
            'pos_config_id': pos_config.id,
            'pos_categ_ids': [(6, 0, kitchen_cats.ids)],
        }
        if existing:
            existing.write(vals)
            print(f"  Updated Kitchen Screen for: {pos_config.name}")
        else:
            screen = KitchenScreen.create(vals)
            print(f"  Created Kitchen Screen for: {pos_config.name} (id={screen.id})")

    env.cr.commit()

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  Kitchen Screen setup complete!")
print("=" * 60)
print(f"""
  Module:       pos_kitchen_screen_odoo
  Group:        Kitchen Cook (assigned to admin users)
  Categories:   {', '.join(found_names) if found_names else '(none found yet)'}
  Linked to:    {len(pos_configs) if pos_configs else 0} POS config(s)

  How to use the kitchen tablet:
  1. Go to Point of Sale > Pos kitchen screen
  2. Create or edit a Kitchen Screen record
  3. Select your POS config and kitchen categories
  4. Click "Kitchen Screen" button to open the kitchen display
  5. Leave it running on a kitchen tablet/TV
""")
print("=" * 60)