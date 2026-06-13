#!/usr/bin/env python3
import base64
import logging
import os

logger = logging.getLogger(__name__)

env = env

print("=" * 60)
print("  Pizzeria El Gordo - Company Logo Setup")
print("=" * 60)

LOGO_PATH = '/images/pizzeria_logo.png'

print("\n[1/1] Setting company logo...")
company = env['res.company'].search([], limit=1)
if company and os.path.isfile(LOGO_PATH):
    with open(LOGO_PATH, 'rb') as f:
        logo_data = base64.b64encode(f.read())
    company.write({'logo': logo_data})
    print(f"  Company '{company.name}' logo set from {LOGO_PATH}")
    print(f"  Logo size: {len(logo_data)} bytes (base64)")
elif not os.path.isfile(LOGO_PATH):
    print(f"  WARNING: Logo file not found at {LOGO_PATH}")
else:
    print("  WARNING: No company found")

env.cr.commit()

print("\n" + "=" * 60)
print("  Company logo setup complete!")
print("=" * 60)
