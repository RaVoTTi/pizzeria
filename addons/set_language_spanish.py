#!/usr/bin/env python3
"""
Set Odoo language to Spanish (es_AR)
Run this via Odoo shell to install and activate Spanish translations
"""

import logging

logger = logging.getLogger(__name__)

env = env

print("=" * 60)
print("  Pizzeria El Gordo - Language Setup (Spanish)")
print("=" * 60)

# Step 1: Activate Spanish language
print("\n[1/3] Activating Spanish language (es_ES)...")
Lang = env['res.lang']
es_lang = Lang.with_context(active_test=False).search([('code', '=', 'es_ES')], limit=1)
if es_lang:
    if not es_lang.active:
        es_lang.write({'active': True})
        print(f"  Activated es_ES (id={es_lang.id})")
    else:
        print(f"  es_ES already active (id={es_lang.id})")
    env.cr.commit()

    # Load translations for es_ES
    print("  Loading translations...")
    try:
        wizard = env['base.language.install'].create({
            'overwrite': True,
        })
        wizard.write({'lang_ids': [(4, es_lang.id)]})
        wizard.lang_install()
        print("  Translations loaded")
    except Exception as e:
        print(f"  Note: Translations may already be loaded: {e}")
else:
    print("  es_ES not found in Odoo's language list.")
    print("  You may need to install it from Settings > Translations > Languages")

# Step 2: Set Spanish as the default language for the company
print("\n[2/3] Setting Spanish as default company language...")
try:
    company = env['res.company'].search([], limit=1)
    if company and company.partner_id:
        company.partner_id.write({'lang': 'es_ES'})
        print(f"  Company '{company.name}' language set to Spanish (es_ES)")
    env.cr.commit()
except Exception as e:
    print(f"  WARNING: Could not update company language: {e}")

# Step 3: Set Spanish for the admin user
print("\n[3/3] Setting Spanish language for admin user...")
try:
    admin = env.ref('base.user_admin', raise_if_not_found=False)
    if not admin:
        admin = env['res.users'].search([('login', '=', 'admin')], limit=1)
    if admin:
        admin.write({'lang': 'es_ES'})
        print(f"  Admin user language set to Spanish (es_ES)")
    env.cr.commit()
except Exception as e:
    print(f"  WARNING: Could not update admin user language: {e}")

print("\n" + "=" * 60)
print("  Language setup complete!")
print("=" * 60)
print("\n  Next steps:")
print("  1. Log out and log back in to see the Spanish interface")
print("  2. Go to Settings > Translations > Languages to manage languages")
print("=" * 60)