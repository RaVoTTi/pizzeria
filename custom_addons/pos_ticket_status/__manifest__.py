{
    'name': 'POS Ticket Status Badge',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Fix ticket status badge colors and terminology',
    'description': 'Fixes the translation mismatch in ticket status badges and uses KDS terminology (FALTA PAGAR / PAGADO)',
    'author': 'Pizzeria El Gordo',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_ticket_status/static/src/js/ticket_status.js',
            'pos_ticket_status/static/src/xml/ticket_status.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
