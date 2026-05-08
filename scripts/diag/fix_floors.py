#!/usr/bin/env python3
"""
Fix floor plan - clean up old floors and fix table identifiers.
"""

print("=" * 70)
print("  Fixing Floor Plan")
print("=" * 70)

import base64
import os

pos_config = env['pos.config'].search([], limit=1)
if not pos_config:
    print("  ERROR: No POS config!")
    exit(1)

print(f"\n  POS Config: {pos_config.name}")

# Close any open sessions
open_sessions = env['pos.session'].search([('state', '!=', 'closed')])
if open_sessions:
    print(f"  Closing {len(open_sessions)} open session(s)...")
    for session in open_sessions:
        try:
            session.action_pos_session_closing_control()
            session.action_pos_session_close()
        except Exception as e:
            print(f"    Warning: {e}")
    env.cr.commit()

# Delete old floors "Salón" and "Afuera" - keep only "El Gordo"
old_floors = env['restaurant.floor'].search([('name', 'in', ['Salón', 'Afuera'])])
if old_floors:
    print(f"\n  Deleting old floors: {', '.join(old_floors.mapped('name'))}")
    old_floors.unlink()
    env.cr.commit()
    print("  Old floors deleted")

# Find or create El Gordo floor
floor = env['restaurant.floor'].search([('name', '=', 'El Gordo')], limit=1)

# Load layout image
layout_path = '/images/layout.png'
if os.path.exists(layout_path):
    with open(layout_path, 'rb') as f:
        layout_image = base64.b64encode(f.read()).decode('utf-8')
    print(f"\n  Loaded layout.png ({len(layout_image)} bytes)")
else:
    print(f"\n  ERROR: layout.png not found!")
    layout_image = None

if floor:
    print(f"\n  Updating 'El Gordo' floor (ID: {floor.id})")
    if layout_image:
        floor.write({'floor_background_image': layout_image})
        print("  ✓ Updated background image")
    
    # Ensure linked to POS
    if pos_config.id not in floor.pos_config_ids.ids:
        floor.write({'pos_config_ids': [(4, pos_config.id)]})
        print("  ✓ Linked to POS config")
    
    # Fix table identifiers
    print("\n  Fixing table identifiers...")
    identifier_map = {
        '777': 'RETIRA',
        '0': 'DELIVERY',
        '6ce50e97': 'RETIRA',  # old messed up identifier
        'd7e097b9': 'DELIVERY',  # old messed up identifier
    }
    
    for table in floor.table_ids:
        if table.table_number == 777 and table.identifier != 'RETIRA':
            table.write({'identifier': 'RETIRA'})
            print(f"    Fixed table 777: identifier → RETIRA")
        elif table.table_number == 0 and table.identifier != 'DELIVERY':
            table.write({'identifier': 'DELIVERY'})
            print(f"    Fixed table 0: identifier → DELIVERY")
    
    env.cr.commit()
    
    print(f"\n  Floor now has {len(floor.table_ids)} tables:")
    for t in floor.table_ids.sorted(lambda x: x.table_number):
        print(f"    Table {t.identifier} (num:{t.table_number}): pos=({t.position_h}, {t.position_v}), size={t.width}x{t.height}")

else:
    print("\n  'El Gordo' floor not found! Run setup_floors.py first.")

print("\n  ✓ Floor plan fixed!")
print("  Refresh browser (Ctrl+Shift+R) to see changes")
print("=" * 70)