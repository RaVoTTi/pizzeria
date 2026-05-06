# -*- coding: utf-8 -*-
{
    "name": "POS Half & Half Pizza Pricing",
    "version": "19.0.2.0.0",
    "category": "Point of Sale",
    "summary": "MAX pricing for Mitad y Mitad (half & half) pizzas in POS",
    "description": """
        Pizzeria El Gordo - Mitad y Mitad Pricing
        ==========================================

        When a cashier selects a "Mitad y Mitad" (half & half) pizza in POS
        with Lado A and Lado B attributes, this module overrides the price
        to be MAX(price_of_pizza_A, price_of_pizza_B).

        This cannot be done with standard Odoo variant pricing (which SUMs
        price_extras). The JS patch runs in the POS frontend for instant
        price updates, even offline.

        Architecture:
        - Stock deduction: handled by phantom BoM (setup_mitad_mitad.py)
        - Pricing: MAX(price_A, price_B) via this JS patch
        - Fallback: base price = most expensive pizza (safety net)
    """,
    "license": "LGPL-3",
    "author": "Pizzeria El Gordo",
    "depends": ["point_of_sale"],
    "data": [],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}