{
    'name': 'POS Thermal Print',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Print thermal receipt from POS receipt screen',
    'description': 'Adds a button to the POS receipt screen to print to thermal printer via CUPS',
    'author': 'Pizzeria El Gordo',
    'depends': ['point_of_sale', 'pos_kitchen_receipt'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_thermal_print/static/src/js/thermal_print_button.js',
            'pos_thermal_print/static/src/js/thermal_print_payment_button.js',
            'pos_thermal_print/static/src/xml/thermal_print_button.xml',
            'pos_thermal_print/static/src/xml/thermal_print_payment_button.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
