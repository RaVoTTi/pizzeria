# -*- coding: utf-8 -*-
{
    'name': 'POS Receipt Logo',
    'version': '19.0.1.0',
    'category': 'Point Of Sale',
    'summary': 'Print Pizzeria El Gordo logo on thermal receipts via ESC/POS',
    'description': """
        Adds logo printing capability to thermal receipts.
        Reads a pre-processed PBM (P4) bitmap from /images/pizzeria_logo.pbm
        and sends it to the kitchen thermal printer via CUPS.
    """,
    'author': 'Pizzeria El Gordo',
    'depends': ['pos_kitchen_screen_odoo'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
