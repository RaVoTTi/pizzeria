{
    'name': 'POS Kitchen Receipt',
    'version': '19.0.1.0',
    'category': 'Point Of Sale',
    'summary': 'Thermal receipt formatting and printing for kitchen tickets',
    'description': """
        Separates ticket printing logic from the kitchen display module.
        Handles ESC/POS formatting, category grouping, and CUPS printing.
        Change ticket layout without touching the KDS module.
    """,
    'author': 'Pizzeria El Gordo',
    'depends': ['pos_kitchen_screen_odoo', 'pos_receipt_logo'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}