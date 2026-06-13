POS / Orders

[x] After clicking the three dots, show Table Number in the delivery/order column.

[x] Review what happens when an order is modified and then canceled.

[x] Add desserts to the menu/products, it should be a new category like panini

[x] Verify order movement/status flow from server → kitchen → delivery/completed (verify exact requirement).

[x] Change the wording of "Price Paid" because it currently only means the order was confirmed, not actually paid(maybe the translation to spanish is weird)


Delivery

[ ] Fix delivery address selection. Current issue: it goes to the saved address, but the correct location may be somewhere else, or asked. like the contact should be saved but. I think that i can adapt that with the custom module, @sale_delivery_address



[x] Fix time / timezone configuration (business hours). It should be the timezone of argentina



POS / Printing

[x] Add ability to print directly from POS, I think that it is there the from the kds the printing function, works well. i think that "Print Complete Receipt" or "imprimir recibo completo" option doesn't call my custom module. Idk check that. 


Products & Menu

[ ] Add photos for the remaining pizzas.

[ ] Add desserts/products that are missing.


Branding

[x] Add pizzeria logo.


[] change the colors of the system for the colors, on @branding/colors.md


Users & Permissions

[x] Create users and roles import from CSV (similar to product import). there is a csv called employees.csv


Kitchen / Oven

[ ] Determine and configure the oven's maximum capacity.



[x] Fix POS time bug (22:30 showed as 18:30 due to UTC conversion) - Standardized: store UTC, display local

[x] Employees are Odoo users with POS PIN access (not just clients)

