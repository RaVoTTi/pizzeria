#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

env = env

print("=" * 60)
print("  Pizzeria El Gordo - Timezone Setup (Argentina)")
print("=" * 60)

field = env['res.partner']._fields['tz']
selection = field.selection
if callable(selection):
    selection = selection(env['res.partner'])

valid_keys = [key for key, label in selection]
print(f"\n  Available timezones: {len(valid_keys)}")

PREFERRED = [
    'America/Buenos_Aires',
    'America/Argentina/Buenos_Aires',
    'America/Cordoba',
    'America/Argentina/Cordoba',
    'America/Mendoza',
    'America/Argentina/Mendoza',
]

TZ = None
for candidate in PREFERRED:
    if candidate in valid_keys:
        TZ = candidate
        break

if not TZ:
    argentina_matches = [k for k in valid_keys if 'buenos' in k.lower() or 'argentina' in k.lower() or 'cordoba' in k.lower()]
    if argentina_matches:
        TZ = argentina_matches[0]
        print(f"  Found matching timezone: {TZ}")
    else:
        print(f"  WARNING: No Argentina timezone found. Available America/* zones:")
        america = [k for k in valid_keys if k.startswith('America/')]
        for a in america[:10]:
            print(f"    {a}")
        if america:
            TZ = america[0]
        else:
            print("  ERROR: No America timezones available at all")
            TZ = valid_keys[0] if valid_keys else None

if not TZ:
    print("  ERROR: Could not determine timezone")
else:
    print(f"\n[1/2] Setting company timezone to {TZ}...")
    company = env['res.company'].search([], limit=1)
    if company and company.partner_id:
        company.partner_id.write({'tz': TZ})
        print(f"  Company '{company.name}' timezone set to {TZ}")
    env.cr.commit()

    print("\n[2/2] Setting timezone for all users...")
    users = env['res.users'].search([('share', '=', False)])
    count = 0
    for user in users:
        if user.partner_id:
            user.partner_id.write({'tz': TZ})
            count += 1
    env.cr.commit()
    print(f"  Updated {count} users")

    print("\n" + "=" * 60)
    print(f"  Timezone set to {TZ} for company and {count} users")
    print("=" * 60)
