# -*- coding: utf-8 -*-
{
    "name": "POS Mitad y Mitad - Tile Configurator",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Tile-based configurator for Mitad y Mitad half-pizzas",
    "description": """
        Two-step wizard for Mitad y Mitad (half &amp; half) pizzas.
        Replaces radio buttons with a touch-friendly tile grid.

        Step 1: Select 1st Half → Step 2: Select 2nd Half → Add to cart

        Uses Odoo's native configurator flow to create the correct variant
        with Lado A / Lado B attribute values, enabling phantom BoM
        conditional lines to deduct 50% of each pizza's ingredients.
    """,
    "license": "LGPL-3",
    "author": "Pizzeria El Gordo",
    "depends": ["point_of_sale", "pos_restaurant", "mrp"],
    "data": [],
    "assets": {
        "point_of_sale.assets": [
            "pos_mitad_configurator/static/src/scss/pos_mitad_configurator.scss",
            "pos_mitad_configurator/static/src/js/pos_mitad_configurator.js",
        ],
        "web.assets_qweb": [
            "pos_mitad_configurator/static/src/xml/pos_mitad_configurator.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}