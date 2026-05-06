#!/usr/bin/env python3
"""
Extract actual table coordinates from Odoo database.
Run this to get the current positions of all tables on the 'El Gordo' floor.

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/extract_coordinates.py
"""

print("=" * 60)
print("  Extracting Table Coordinates from Database")
print("=" * 60)

floor = env['restaurant.floor'].search([('name', '=', 'El Gordo')], limit=1)
if not floor:
    print("\n  ERROR: Floor 'El Gordo' not found!")
    exit(1)

tables = env['restaurant.table'].search([('floor_id', '=', floor.id)])

print(f"\n  Found {len(tables)} tables on floor '{floor.name}'")
print(f"  Floor ID: {floor.id}")
print("\n" + "=" * 60)
print("# --- COPY THIS INTO YOUR SCRIPT ---")
print("# Image size: 1476x650 pixels")
print("all_tables = [")
print("    # Format: (table_num, pos_x, pos_y, width, height, shape, identifier)")

for t in tables.sorted(key=lambda r: r.table_number or 0):
    # Format: (number, x, y, width, height, shape, identifier)
    print(f"    ({t.table_number}, {int(t.position_h)}, {int(t.position_v)}, {int(t.width)}, {int(t.height)}, '{t.shape}', '{t.identifier}'),")

print("]")
print("=" * 60)
