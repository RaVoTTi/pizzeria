#!/usr/bin/env python3
"""
Migration script: backfill order_type for existing pos.order and pos.kitchen.ticket records.
Run via: docker exec -it <web_container> python3 /mnt/addons/migrate_order_type.py
Or via odoo shell: exec(open('/mnt/addons/migrate_order_type.py').read())
"""

def migrate_order_type(env):
    orders = env['pos.order'].search([('order_type', '=', False)])
    count_orders = 0
    for o in orders:
        if o.table_id:
            o.order_type = 'mesa'
        elif o.partner_id and o.partner_id.street:
            o.order_type = 'delivery'
        else:
            o.order_type = 'retira'
        count_orders += 1
    print(f"Migrated {count_orders} pos.order records")

    tickets = env['pos.kitchen.ticket'].search([('order_type', '=', False)])
    count_tickets = 0
    for t in tickets:
        if t.table_id:
            t.order_type = 'mesa'
        elif t.partner_id and t.partner_id.street:
            t.order_type = 'delivery'
        else:
            t.order_type = 'retira'
        count_tickets += 1
    print(f"Migrated {count_tickets} pos.kitchen.ticket records")

    env.cr.commit()
    print("Migration complete. Changes committed.")


if __name__ == '__main__':
    from odoo import api, SUPERUSER_ID
    import odoo.tools as tools
    registry = tools.config['db_name']
    with api.Environment.manage():
        with odoo.registry(registry).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            migrate_order_type(env)
else:
    migrate_order_type(env)
