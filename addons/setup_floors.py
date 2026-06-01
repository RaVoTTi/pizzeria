#!/usr/bin/env python3
"""
Setup restaurant floor plan for Pizzeria El Gordo.

Creates a single combined floor:
  - "El Gordo" with all 19 tables (indoor + outdoor)

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py
"""

import base64
import os

print("=" * 60)
print("  Setting Up Restaurant Floor Plan")
print("=" * 60)

IMAGES_DIR = '/images'

# Check if pos_restaurant module is installed
try:
    env['restaurant.floor']
except KeyError:
    print("\n  ERROR: pos_restaurant module is not installed!")
    print("  Install it first via the UI or run:")
    print("    docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo -i pos_restaurant --stop-after-init")
    exit(1)

# Get or create Salon POS config (floor is only for dine-in)
pos_config = env['pos.config'].search([('name', '=', 'POS Salon')], limit=1)
if not pos_config:
    pos_config = env['pos.config'].search([], limit=1)
    if pos_config:
        print(f"\n  Using existing POS config: {pos_config.name} (id={pos_config.id})")
    else:
        print("\n  No POS config found, creating POS Salon...")

        # Ensure a bank journal exists (required by pos.config default values)
        company = env.company
        bank_journal = env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'bank'),
        ], limit=1)
        if not bank_journal:
            print("  Creating bank journal (required for POS)...")
            bank_account = env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'asset_current'),
            ], limit=1)
            if not bank_account:
                bank_account = env['account.account'].create({
                    'name': 'Bank',
                    'code': '1100',
                    'account_type': 'asset_current',
                    'company_id': company.id,
                })
                env.cr.commit()
                print(f"  Created bank account: {bank_account.name}")
            bank_journal = env['account.journal'].create({
                'name': 'Bank',
                'code': 'BNK1',
                'type': 'bank',
                'company_id': company.id,
                'default_account_id': bank_account.id,
            })
            env.cr.commit()
            print(f"  Created bank journal: {bank_journal.name}")

        pos_config = env['pos.config'].create({
            'name': 'POS Salon',
        })
        print(f"  Created POS config: POS Salon (id={pos_config.id})")
else:
    print(f"\n  Using POS config: {pos_config.name} (id={pos_config.id})")

# Configure POS for restaurant mode
if not pos_config.module_pos_restaurant:
    print("\n  Enabling restaurant mode...")
    pos_config.write({'module_pos_restaurant': True})
    print("  Restaurant mode enabled")

# ============================================================================
# SINGLE FLOOR: EL GORDO (Combined Indoor + Outdoor)
# ============================================================================
print("\n[1/1] Setting up 'El Gordo' floor...")

# Load layout image
layout_path = os.path.join(IMAGES_DIR, 'layout.png')
layout_image = None
if os.path.exists(layout_path):
    with open(layout_path, 'rb') as f:
        layout_image = base64.b64encode(f.read()).decode('utf-8')
    print(f"  Loaded layout.png ({len(layout_image)} bytes)")
else:
    print(f"  WARNING: layout.png not found at {layout_path}")

# Clear draft orders first (required before closing sessions)
draft_orders = env['pos.order'].search([('state', '=', 'draft')])
if draft_orders:
    print(f"  Removing {len(draft_orders)} draft POS order(s)...")
    draft_orders.unlink()
    env.cr.commit()
    print("  Draft orders removed")

# Close any open POS sessions first (required before modifying floors)
open_sessions = env['pos.session'].search([('state', '!=', 'closed')])
if open_sessions:
    print(f"  Closing {len(open_sessions)} open POS session(s)...")
    for session in open_sessions:
        try:
            session.action_pos_session_closing_control()
            session.action_pos_session_close()
            print(f"    Closed session: {session.name}")
        except Exception as e:
            print(f"    Warning: Could not close session {session.name}: {e}")
    env.cr.commit()
    print("  Sessions closed")

# Remove old floors from POS config (don't delete - they have active sessions)
old_floors = env['restaurant.floor'].search([('name', 'in', ['Salón', 'Afuera'])])
if old_floors:
    print(f"  Removing {len(old_floors)} old floor(s) from POS config: {', '.join(old_floors.mapped('name'))}")
    # Unlink from POS config (remove relationship) but don't delete the floors
    for old_floor in old_floors:
        old_floor.write({'pos_config_ids': [(3, pos_config.id)]})  # (3, id) removes from many2many

# Create or update El Gordo floor
floor = env['restaurant.floor'].search([('name', '=', 'El Gordo')], limit=1)
if floor:
    print(f"  Floor 'El Gordo' already exists (id={floor.id})")
    if layout_image:
        floor.write({'floor_background_image': layout_image})
        print("  Updated floor plan image")
    # Ensure it's linked to the POS config
    if pos_config.id not in floor.pos_config_ids.ids:
        floor.write({'pos_config_ids': [(4, pos_config.id)]})
        print("  Linked floor to POS config")
else:
    vals = {
        'name': 'El Gordo',
        'pos_config_ids': [(4, pos_config.id)],
    }
    if layout_image:
        vals['floor_background_image'] = layout_image
    
    floor = env['restaurant.floor'].create(vals)
    print(f"  Created floor 'El Gordo' (id={floor.id})")

# Create all tables for the combined floor
# Image size: 1476x650 pixels
print("  Creating tables...")


all_tables = [
    # Format: (table_num, pos_x, pos_y, width, height, shape, identifier)
    # --- INDOOR SECTION (Left / Beige) ---
    (1, 441, 34, 97, 71, 'square', '1'),
    (2, 444, 104, 90, 62, 'square', '2'),
    (3, 586, 41, 86, 87, 'square', '3'),
    (4, 696, 42, 80, 82, 'square', '4'),
    (5, 495, 225, 130, 78, 'square', '5'),
    (6, 652, 338, 78, 78, 'square', '6'),
    (7, 438, 399, 96, 89, 'square', '7'),
    (8, 500, 560, 224, 68, 'square', '8 Barra'),
    (9, 52, 33, 79, 58, 'square', '9'),
    (10, 165, 33, 74, 58, 'square', '10'),
    (11, 43, 134, 76, 60, 'square', '11'),
    (12, 157, 136, 71, 59, 'square', '12'),
    # --- OUTDOOR SECTION (Middle-Right / Blue) ---
    (13, 896, 81, 95, 94, 'square', '13'),
    (14, 1045, 84, 93, 94, 'square', '14'),
    (15, 898, 285, 95, 94, 'square', '15'),
    (16, 1046, 290, 92, 92, 'square', '16'),
    # --- SPECIAL BUTTONS (Far Right) ---

]

for table_num, pos_x, pos_y, width, height, shape, identifier in all_tables:
    existing = env['restaurant.table'].search([
        ('floor_id', '=', floor.id),
        ('table_number', '=', table_num),
    ], limit=1)
    
    if existing:
        print(f"    Table {identifier} already exists - updating position")
        existing.write({
            'position_h': pos_x,
            'position_v': pos_y,
            'width': width,
            'height': height,
        })
        continue
    
    env['restaurant.table'].create({
        'table_number': table_num,
        'identifier': identifier,
        'floor_id': floor.id,
        'position_h': pos_x,
        'position_v': pos_y,
        'width': width,
        'height': height,
        'shape': shape,
        'seats': 4 if shape == 'square' else 4,
    })
    print(f"    Created table {identifier}")

env.cr.commit()

print("\n" + "=" * 60)
print("  Floor plan setup complete!")
print("=" * 60)
print("\n  Floor created:")
print(f"    • El Gordo: 18 tables")
print(f"      - Indoor: 12 tables (1-12, including Barra)")
print(f"      - Outdoor: 4 tables (13-16)")
print(f"      - Special: 2 buttons (DELIVERY, RETIRA)")
print(f"\n  Image size: 1476x650 pixels")
print("\n  NOTE: If background image and table positions don't align:")
print("    1. Open POS → Edit Mode (pencil icon)")
print("    2. Drag table boxes to match image positions")
print("    3. Save changes")
print("\n  Refresh browser to see floor plan in POS (Ctrl+Shift+R)")
print("=" * 60)
