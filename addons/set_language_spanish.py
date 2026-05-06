#!/usr/bin/env python3
"""
Set Odoo language to Spanish (es_ES)
Run this via Odoo shell to install and activate Spanish translations
"""

import logging

logger = logging.getLogger(__name__)

env = env

print("=" * 60)
print("  Pizzeria El Gordo - Language Setup (Spanish)")
print("=" * 60)

# Step 1: Install Spanish language
print("\n[1/3] Installing Spanish language pack (es_ES)...")
try:
    # Load Spanish translation
    lang_code = 'es_ES'
    
    # Check if language already installed
    existing_lang = env['res.lang'].search([('code', '=', lang_code)], limit=1)
    
    if existing_lang and existing_lang.active:
        print(f"  Spanish (es_ES) is already installed and active")
    else:
        # Install the language using the wizard
        wizard = env['base.language.install'].create({
            'lang': lang_code,
            'overwrite': False,
        })
        wizard.lang_install()
        print(f"  Spanish (es_ES) language pack installed successfully")
    
    env.cr.commit()
    
except Exception as e:
    print(f"  WARNING: Could not install language pack: {e}")
    print("  You may need to install it manually from Settings → Translations")

# Step 2: Set Spanish as the default language for the company
print("\n[2/3] Setting Spanish as default company language...")
try:
    company = env['res.company'].search([], limit=1)
    if company:
        company.write({'partner_id': company.partner_id.id})  # Ensure partner exists
        # Set the language on the partner (which controls company language)
        if company.partner_id:
            company.partner_id.write({'lang': 'es_ES'})
            print(f"  Company '{company.name}' language set to Spanish (es_ES)")
    else:
        print("  No company found to update")
    
    env.cr.commit()
    
except Exception as e:
    print(f"  WARNING: Could not update company language: {e}")

# Step 3: Set Spanish for the admin user
print("\n[3/3] Setting Spanish language for admin user...")
try:
    admin_user = env.ref('base.user_admin')
    if admin_user:
        admin_user.write({'lang': 'es_ES'})
        print(f"  Admin user language set to Spanish (es_ES)")
    else:
        # Fallback: search for the first administrator
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
print("  2. Go to Settings → Translations → Languages to manage languages")
print("  3. For new users, Spanish will be the default language")
print("=" * 60)
