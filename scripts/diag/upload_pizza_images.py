#!/usr/bin/env python3
"""
Upload pizza images to products.

Place pizza images in /images/pizzas/ directory with filenames matching product names:
  - Mozzarella.jpg or Mozzarella.png
  - Especial.jpg or Especial.png
  - etc.

The script will match filenames to product names and upload the images.

Usage:
    docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/upload_pizza_images.py
"""

import os
import base64

print("=" * 70)
print("  Upload Pizza Images to Products")
print("=" * 70)

IMAGES_DIR = '/images/pizzas'

# Check if directory exists
if not os.path.exists(IMAGES_DIR):
    print(f"\n  ERROR: Directory {IMAGES_DIR} does not exist!")
    print(f"  Create it and add pizza images:")
    print(f"    mkdir -p images/pizzas")
    print(f"    # Copy your pizza images there")
    exit(1)

# Get all image files
image_files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
if not image_files:
    print(f"\n  No images found in {IMAGES_DIR}")
    print(f"  Add images with names matching pizza products:")
    print(f"    - Mozzarella.png")
    print(f"    - Especial.jpg")
    print(f"    - etc.")
    exit(1)

print(f"\n  Found {len(image_files)} images in {IMAGES_DIR}:")
for f in image_files:
    print(f"    {f}")

ProductTemplate = env['product.template']

# Match images to products
updated = 0
not_found = []

for image_file in image_files:
    # Remove extension to get product name
    name_without_ext = os.path.splitext(image_file)[0]
    
    # Try exact match first
    product = ProductTemplate.search([('name', '=', name_without_ext)], limit=1)
    
    # If not found, try case-insensitive
    if not product:
        product = ProductTemplate.search([('name', 'ilike', name_without_ext)], limit=1)
    
    if not product:
        not_found.append(name_without_ext)
        print(f"  WARNING: No product found for '{image_file}'")
        continue
    
    # Read and encode image
    image_path = os.path.join(IMAGES_DIR, image_file)
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read())
    
    # Upload to product
    product.write({'image_1920': image_data})
    updated += 1
    print(f"  ✓ {product.name}: uploaded {image_file} ({len(image_data)} bytes)")

env.cr.commit()

print(f"\n  Updated {updated} products with images")
if not_found:
    print(f"  Could not find products for: {', '.join(not_found)}")

# Show products without images
pizzas = ProductTemplate.search([('categ_id.name', '=', 'Pizzas')])
without_images = [p.name for p in pizzas if not p.image_1920]
if without_images:
    print(f"\n  Pizzas still without images ({len(without_images)}):")
    for name in without_images:
        print(f"    - {name}")
    print(f"\n  Add images named: {', '.join(without_images[:3])}...")

print("=" * 70)