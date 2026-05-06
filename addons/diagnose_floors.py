#!/usr/bin/env python3
"""
Diagnose floor plan issues.
"""

print("=" * 70)
print("  Floor Plan Diagnostics")
print("=" * 70)

# Check if pos_restaurant is installed
try:
    env['restaurant.floor']
    print("\n  ✓ pos_restaurant module is installed")
except KeyError:
    print("\n  ✗ pos_restaurant module is NOT installed!")
    exit(1)

# Check POS config
pos_config = env['pos.config'].search([], limit=1)
if pos_config:
    print(f"\n  POS Config: {pos_config.name}")
    print(f"    module_pos_restaurant: {pos_config.module_pos_restaurant}")
else:
    print("\n  ✗ No POS config found!")

# Check floors
print("\n  Floors:")
floors = env['restaurant.floor'].search([])
if not floors:
    print("    ✗ No floors found!")
else:
    for floor in floors:
        has_image = bool(floor.floor_background_image)
        image_size = len(floor.floor_background_image) if has_image else 0
        table_count = len(floor.table_ids)
        pos_configs = floor.pos_config_ids.mapped('name')
        
        print(f"\n    Floor: {floor.name}")
        print(f"      ID: {floor.id}")
        print(f"      Background image: {'✓ Yes' if has_image else '✗ No'} ({image_size} bytes)")
        print(f"      Tables: {table_count}")
        print(f"      Linked to POS configs: {', '.join(pos_configs) if pos_configs else '✗ None'}")
        
        if table_count > 0:
            print(f"      Table list:")
            for table in floor.table_ids:
                print(f"        - {table.identifier} (pos: {table.position_h}, {table.position_v}, size: {table.width}x{table.height})")

# Check if layout.png exists in container
import os
layout_path = '/images/layout.png'
if os.path.exists(layout_path):
    size = os.path.getsize(layout_path)
    print(f"\n  ✓ layout.png exists in container ({size} bytes)")
else:
    print(f"\n  ✗ layout.png NOT found at {layout_path}")
    print(f"     Check docker-compose.yml volume mount: ./images:/images:ro")

print("=" * 70)