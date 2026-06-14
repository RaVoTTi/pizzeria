use the structure that @custom_addons/custom_receipts_for_pos/, because i need to print my ticket on the pos, so use @custom_addons/custom_receipts_for_pos/ as an example of how to implement my @custom_addons/pos_kitchen_receipt/. I want to print my receipt from the pos, use @custom_addons/pos_takeaway/ as an example of how to add a button(like entregado)
 dir  custom_addons/custom_receipts_for_pos/ 
 dir  custom_addons/pos_kitchen_receipt/ 
 dir  custom_addons/pos_takeaway/ 
Thinking: The user wants me to:
1. Use custom_receipts_for_pos/ as an example of how to implement printing from POS
2. Use pos_takeaway/ as an example of how to add a button (like "entregado")
3. Implement printing the receipt from POS using pos_kitchen_receipt/ as the base
Let me first explore these modules to understand their structure and then implement the solution.
Let me break this down:
- Read custom_receipts_for_pos/ to understand how they handle printing from POS
- Read pos_takeaway/ to understand how they add buttons to POS
- Read pos_kitchen_receipt/ to understand the existing thermal printer implementation
- Then create a solution that adds a print button to POS that calls the thermal printer
Let me start by exploring these modules.
Let me explore these modules to understand the patterns.
│ Explore Task — Explore custom_receipts_for_pos module
└ 15 toolcalls · 2m 52s
│ Explore Task — Explore pos_takeaway module
└ 19 toolcalls · 2m 21s
│ Explore Task — Explore pos_kitchen_receipt module
└ 9 toolcalls · 1m 8s
ctrl+x down view subagents
Thinking: Now I have a clear picture of all three modules. Let me understand what the user wants:
1. Use custom_receipts_for_pos/ as an example - This module shows how to customize the POS receipt by patching OrderReceipt.prototype and using template inheritance. It uses a dynamic OWL component approach where the receipt template is stored as XML text in the database.
2. Use pos_takeaway/ as an example - This module shows how to add buttons to the POS control buttons by patching ControlButtons.prototype and using template inheritance with xpath.
3. Use pos_kitchen_receipt/ as the base - This module has the thermal printer logic (ESC/POS formatting, CUPS printing, logo).
The user wants to:
- Add a button to the POS (like "Entregado" or "Imprimir") that prints the receipt to the thermal printer
- Use the existing pos_kitchen_receipt module's formatting/printing logic
- Follow the patterns from custom_receipts_for_pos and pos_takeaway
Looking at the existing code, I already created pos_kitchen_screen_odoo/static/src/js/receipt_print.js which patches PosStore.prototype.printReceipt() to call pos.order.print_customer_receipt() via RPC. And I added the print_customer_receipt() method to pos.order in pos_kitchen_screen_odoo/models/pos_orders.py.
But the user wants me to restructure this properly. Let me think about what needs to happen:
1. The pos_kitchen_receipt module already has the ESC/POS formatting and CUPS printing logic
2. I need to add a method to format and print a customer receipt (not just a kitchen ticket)
3. I need to add a button to the POS that triggers this printing
Actually, looking more carefully at the user's request:
- "i need to print my ticket on the pos" - they want to print from POS
- "use custom_receipts_for_pos as an example of how to implement my pos_kitchen_receipt" - they want to follow the pattern of custom_receipts_for_pos
- "use pos_takeaway as an example of how to add a button(like entregado)" - they want to add a button like the takeaway module does
So the approach should be:
1. Add a method to pos.order (or extend pos_kitchen_receipt) that formats a customer receipt as ESC/POS and prints it
2. Add a button to the POS receipt screen that calls this method via RPC
3. Follow the patterns from the example modules
Let me think about the architecture:
Option A: Extend pos_kitchen_receipt
- Add a new method to kitchen.ticket.printer that formats a customer receipt (different from kitchen ticket)
- Or add a new model pos.receipt.printer that handles customer receipt printing
Option B: Create a new module
- Create pos_thermal_receipt that depends on pos_kitchen_receipt and point_of_sale
- Add the button and RPC method here
I think Option B is cleaner - create a new module that bridges the POS and the thermal printer. But actually, the user said "use pos_kitchen_receipt as an example" - they might want me to just add the functionality to the existing module.
Let me re-read: "i need to print my ticket on the pos, so use custom_receipts_for_pos as an example of how to implement my pos_kitchen_receipt"
I think they want me to:
1. Add a button to the POS (following pos_takeaway pattern)
2. That button triggers printing to the thermal printer (using pos_kitchen_receipt logic)
3. Follow the custom_receipts_for_pos pattern for how to structure the POS integration
Let me create a new module pos_thermal_print that:
1. Depends on pos_kitchen_receipt and point_of_sale
2. Adds a method to pos.order that calls the kitchen receipt printer
3. Adds a button to the POS receipt screen that triggers this
Actually, I already have some of this in pos_kitchen_screen_odoo:
- pos_kitchen_screen_odoo/static/src/js/receipt_print.js - patches PosStore.printReceipt()
- pos_kitchen_screen_odoo/models/pos_orders.py - has print_customer_receipt() method
But this is in the wrong module. The user wants it properly structured.
Let me think about the cleanest approach:
1. Create a new module pos_thermal_print that:
   - Depends on pos_kitchen_receipt (for the printer logic)
   - Adds a method to pos.order that formats and prints a customer receipt
   - Adds a button to the POS receipt screen
Actually, looking at the existing code again, I think the simplest approach is:
1. Add a print_thermal_receipt() method to pos.order that creates a kitchen ticket and prints it
2. Add a button to the POS receipt screen that calls this method
But wait - the user wants a customer receipt, not a kitchen ticket. The kitchen ticket format is for the kitchen staff, not for the customer.
Let me think about this differently. The user wants:
1. A button on the POS (like "Imprimir Recibo" or "Entregado")
2. When clicked, it prints a receipt to the thermal printer
3. The receipt should be customer-facing (not kitchen ticket format)
So I need to:
1. Create a customer receipt formatter (similar to kitchen ticket but with customer receipt layout)
2. Add a button to the POS
3. Connect them
Actually, looking at the existing print_customer_receipt() method I added to pos.order:
def print_customer_receipt(self):
    self.ensure_one()
    ticket = self.env["pos.kitchen.ticket"].search([
        ("origin_pos_order_id", "=", self.id),
        ("ticket_type", "=", "new"),
    ], limit=1)
    if not ticket:
        ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(self)
    if ticket:
        return ticket.print_ticket()
    return False
This just finds the kitchen ticket and prints it. But the kitchen ticket format is not ideal for a customer receipt.
Let me create a proper customer receipt formatter. I'll add it to the pos_kitchen_receipt module since that's where the printer logic lives.
Actually, let me re-read the user's request one more time:
"i need to print my ticket on the pos, so use custom_receipts_for_pos as an example of how to implement my pos_kitchen_receipt. I want to print my receipt from the pos, use pos_takeaway as an example of how to add a button(like entregado)"
I think the user wants:
1. To print the receipt from the POS screen (not just from KDS)
2. Use the pattern from custom_receipts_for_pos for how to structure the POS integration
3. Use the pattern from pos_takeaway for how to add a button
So the approach is:
1. Add a button to the POS receipt screen (following pos_takeaway pattern)
2. That button triggers printing to the thermal printer (using pos_kitchen_receipt logic)
3. Follow the custom_receipts_for_pos pattern for the module structure
Let me create a new module pos_thermal_print that:
1. Depends on pos_kitchen_receipt and point_of_sale
2. Adds a method to pos.order that formats and prints a customer receipt
3. Adds a button to the POS receipt screen
Actually, I think the simplest approach is to:
1. Add a print_thermal_receipt() method to pos.order in pos_kitchen_receipt
2. Create a new module pos_thermal_print_button that adds the button to POS
But that's splitting it into two modules. Let me just create one module that does both.
Let me create pos_thermal_print:
- Depends on pos_kitchen_receipt
- Adds print_thermal_receipt() to pos.order
- Adds a button to the POS receipt screen
- Follows the patterns from the example modules
Actually, I realize I should just add the functionality to the existing pos_kitchen_receipt module. It already has the printer logic, so I can add:
1. A method to format a customer receipt (different from kitchen ticket)
2. A method to print it
3. Then create a separate small module just for the POS button
Let me start by creating the customer receipt formatter in pos_kitchen_receipt, then create a small module for the POS button.
Wait, I'm overcomplicating this. Let me just:
1. Add a method to pos.order that prints the kitchen ticket (already done)
2. Create a new module that adds a button to POS
Actually, the existing print_customer_receipt() method already does this. I just need to:
1. Create a new module pos_thermal_print that adds the button
2. Or add the button to an existing module
Let me create a new module pos_thermal_print that:
1. Depends on pos_kitchen_screen_odoo (for the print_customer_receipt method)
2. Adds a button to the POS receipt screen
Actually, I think the cleanest approach is to:
1. Move the print_customer_receipt() method to pos_kitchen_receipt (since that's where the printer logic is)
2. Create a new module pos_thermal_print that adds the button to POS
Let me start implementing this.
First, I'll add the print_customer_receipt() method to pos.order in pos_kitchen_receipt:
# pos_kitchen_receipt/models/pos_order.py
from odoo import models
class PosOrder(models.Model):
    _inherit = "pos.order"
    def print_thermal_receipt(self):
        self.ensure_one()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", self.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(self)
        if ticket:
            return self.env["kitchen.ticket.printer"].print_ticket(ticket)
        return False
Then, I'll create a new module pos_thermal_print that adds the button:
pos_thermal_print/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── pos_order.py
└── static/src/
    ├── js/
    │   └── thermal_print_button.js
    └── xml/
        └── thermal_print_button.xml
Let me implement this now.
Actually, I realize I should check if there's already a print_customer_receipt method in pos_kitchen_screen_odoo. Let me check the existing code.
From the earlier exploration, I added this to pos_kitchen_screen_odoo/models/pos_orders.py:
def print_customer_receipt(self):
    self.ensure_one()
    ticket = self.env["pos.kitchen.ticket"].search([
        ("origin_pos_order_id", "=", self.id),
        ("ticket_type", "=", "new"),
    ], limit=1)
    if not ticket:
        ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(self)
    if ticket:
        return ticket.print_ticket()
    return False
And I added a JS patch in pos_kitchen_screen_odoo/static/src/js/receipt_print.js:
/** @odoo-module */
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
patch(PosStore.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
    },
    async printReceipt(options = {}) {
        const result = await super.printReceipt(...arguments);
        const order = options.order || this.getOrder();
        if (order && order.server_id) {
            try {
                await this.orm.call("pos.order", "print_customer_receipt", [order.server_id]);
                this.notification.add("Ticket enviado a impresora", { type: "info" });
            } catch (error) {
                console.error("Error printing to thermal printer:", error);
            }
        }
        return result;
    },
});
So the functionality is already there, but it's in the wrong module. The user wants it properly structured following the patterns from the example modules.
Let me create a proper module structure. I'll:
1. Create a new module pos_thermal_print that:
   - Depends on pos_kitchen_receipt and point_of_sale
   - Adds the print_thermal_receipt() method to pos.order
   - Adds a button to the POS receipt screen
Let me implement this now.
Actually, I think the simplest approach is to just create a new module that adds the button to POS. The print_customer_receipt() method is already in pos_kitchen_screen_odoo, so I can just create a module that adds the button and calls that method.
But the user wants me to follow the pattern from custom_receipts_for_pos, which shows how to properly structure a POS module. Let me look at what that pattern is:
1. It has a models/ directory with Python models
2. It has a static/src/ directory with JS and XML
3. It uses point_of_sale._assets_pos in the manifest to load the JS and XML
4. It patches POS components using patch()
So I should create a module with:
1. __manifest__.py with point_of_sale._assets_pos assets
2. static/src/js/ with JS patches
3. static/src/xml/ with XML template extensions
4. Optionally models/ if I need to add methods to pos.order
Let me create the module now.
I'll create pos_thermal_print:
pos_thermal_print/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── pos_order.py
└── static/src/
    ├── js/
    │   └── thermal_print_button.js
    └── xml/
        └── thermal_print_button.xml
Let me implement this.
Actually, I realize I should just add the functionality to the existing modules rather than creating a new one. The pos_kitchen_receipt module already has the printer logic, so I can add the print_thermal_receipt() method there. And I can add the button to the POS by creating a small module or adding it to an existing one.
Let me think about the cleanest approach:
1. Add print_thermal_receipt() to pos.order in pos_kitchen_receipt
2. Create a new module pos_thermal_print that adds the button to POS
This way, the printer logic stays in pos_kitchen_receipt, and the POS integration is in a separate module.
Let me implement this now.
Actually, I think I'm overthinking this. The user just wants me to:
1. Add a button to the POS that prints to the thermal printer
2. Follow the patterns from the example modules
The existing code already has the print_customer_receipt() method and the JS patch. I just need to:
1. Create a proper module structure
2. Add a button to the POS receipt screen (not just patch printReceipt())
Let me create a new module pos_thermal_print that:
1. Depends on pos_kitchen_screen_odoo (for the print_customer_receipt method)
2. Adds a button to the POS receipt screen that calls this method
Actually, I think the cleanest approach is to:
1. Move the print_customer_receipt() method to pos_kitchen_receipt (since that's where the printer logic is)
2. Create a new module pos_thermal_print that adds the button to POS
Let me implement this now.
OK let me just start coding. I'll:
1. Add print_thermal_receipt() to pos.order in pos_kitchen_receipt/models/pos_order.py
2. Create a new module pos_thermal_print that adds the button to POS
Let me start.
Now I understand the patterns. Let me create a proper module structure following these examples.
# Todos
[ ] 
Add print_thermal_receipt() method to pos.order in pos_kitchen_receipt
[ ] 
Create pos_thermal_print module with button on POS receipt screen
[ ] 
Add JS patch for thermal print button (following pos_takeaway pattern)
[ ] 
Add XML template for thermal print button
[ ] 
Test and verify the implementation
Thinking: Let me start implementing. First, I'll add the print_thermal_receipt() method to pos.order in the pos_kitchen_receipt module.
# Todos
[•] 
Add print_thermal_receipt() method to pos.order in pos_kitchen_receipt
[ ] 
Create pos_thermal_print module with button on POS receipt screen
[ ] 
Add JS patch for thermal print button (following pos_takeaway pattern)
[ ] 
Add XML template for thermal print button
[ ] 
Test and verify the implementation
Thinking: Let me first check the current state of pos_kitchen_receipt to see what files exist and what I need to add.
→ Read custom_addons/pos_kitchen_receipt/models 
Thinking: I need to:
1. Add a pos_order.py file to pos_kitchen_receipt/models/ with the print_thermal_receipt() method
2. Update models/__init__.py to import it
3. Create the new pos_thermal_print module with the button
Let me start.
→ Read custom_addons/pos_kitchen_receipt/models/__init__.py 
Thinking: Now let me create the pos_order.py file in pos_kitchen_receipt/models/ and update the init.py.
# Wrote custom_addons/pos_kitchen_receipt/models/pos_order.py
# -*- coding: utf-8 -*-
from odoo import models
class PosOrder(models.Model):
    _inherit = "pos.order"
    def print_thermal_receipt(self):
        self.ensure_one()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", self.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(self)
        if ticket:
            return self.env["kitchen.ticket.printer"].print_ticket(ticket)
        return False
← Edit custom_addons/pos_kitchen_receipt/models/__init__.py
from . import ticket_printer
from . import ticket_printer
from . import pos_order
Thinking: Now I need to update the manifest to include the pos_order model. Actually, since it's a Python model, it doesn't need to be in the manifest's data files - it's automatically loaded via the init.py.
Now let me create the pos_thermal_print module. I'll follow the pos_takeaway pattern for the button structure.
# Todos
[✓] 
Add print_thermal_receipt() method to pos.order in pos_kitchen_receipt
[•] 
Create pos_thermal_print module with button on POS receipt screen
[ ] 
Add JS patch for thermal print button (following pos_takeaway pattern)
[ ] 
Add XML template for thermal print button
[ ] 
Test and verify the implementation
Thinking: Now let me create the pos_thermal_print module. I need to:
1. Create the directory structure
2. Create manifest.py
3. Create init.py
4. Create models/pos_order.py (if needed)
5. Create static/src/js/thermal_print_button.js
6. Create static/src/xml/thermal_print_button.xml
Let me look at the POS receipt screen structure to understand where to add the button. I need to check how the receipt screen is structured in Odoo 19.
# Find receipt screen files in POS
$ docker compose run --rm web find /usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src -name "*receipt*" -type f 2>/dev/null | head -20
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/css/pos_receipts.css
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/store/order_change_receipt_template.xml
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/screens/receipt_screen/receipt_screen.scss
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/screens/receipt_screen/receipt_screen.xml
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/screens/receipt_screen/receipt_screen.js
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/screens/receipt_screen/receipt/receipt_header/receipt_header.js
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/screens/receipt_screen/receipt/receipt_header/receipt_header.xml
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/screens/receipt_screen/receipt/order_receipt.js
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/screens/receipt_screen/receipt/order_receipt.xml
/usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/components/popups/cash_move_popup/cash_move_receipt/cash_move_receipt.xml
…
Click to expand
Thinking: Let me read the receipt_screen.xml to understand the structure and find where to add the button.
# Read receipt screen XML template
$ docker compose run --rm web cat /usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/screens/receipt_screen/receipt_screen.xml 2>/dev/null
<?xml version="1.0" encoding="UTF-8"?>
<templates id="template" xml:space="preserve">
    <t t-name="point_of_sale.ReceiptScreen">
        <div class="receipt-screen screen h-100 bg-100">
            <div class="screen-content d-flex flex-column h-100">
                <div class="default-view d-flex flex-lg-row flex-column overflow-hidden flex-grow-1">
                    <div class="actions d-flex flex-column justify-content-between flex-lg-grow-1 flex-grow-0 flex-shrink-1 flex-basis-0 border-end">
                        <div class="o_payment_successful d-flex flex-column w-100 w-xxl-75 p-3 pt-xxl-5 mx-auto">
                            <div class="d-flex flex-column align-items-center mb-3 p-1 p-lg-3 border border-success rounded-3 bg-success-subtle text-success fs-3">
…
Click to expand
Thinking: Now I understand the receipt screen structure. I can see there are already "Print Full Receipt" and "Print Basic Receipt" buttons. I need to add a "Print Thermal" button that calls the thermal printer.
Let me also check the receipt_screen.js to understand the component structure.
# Read receipt screen JS
$ docker compose run --rm web cat /usr/lib/python3/dist-packages/odoo/addons/point_of_sale/static/src/app/screens/receipt_screen/receipt_screen.js 2>/dev/null
import { _t } from "@web/core/l10n/translation";
import { useErrorHandlers, useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { registry } from "@web/core/registry";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { useState, Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { isValidEmail } from "@point_of_sale/utils";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
…
Click to expand
Thinking: Now I understand the structure. The ReceiptScreen component has:
- doFullPrint - calls this.pos.printReceipt({ order: this.currentOrder })
- doBasicPrint - calls this.pos.printReceipt({ order: this.currentOrder, basic: true })
I need to add a doThermalPrint method that calls the thermal printer via RPC.
Let me create the pos_thermal_print module following the pos_takeaway pattern.
The module structure will be:
pos_thermal_print/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── pos_order.py (if needed)
└── static/src/
    ├── js/
    │   └── thermal_print_button.js
    └── xml/
        └── thermal_print_button.xml
Let me create this module now.
# Create pos_thermal_print module directory structure
$ mkdir -p /home/fasedaff/Documents/odoo-pizzeria/custom_addons/pos_thermal_print/{models,static/src/{js,xml}}
(no output)
Thinking: Let me create the module files now.
# Wrote custom_addons/pos_thermal_print/__manifest__.py
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
            'pos_thermal_print/static/src/xml/thermal_print_button.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
# Wrote custom_addons/pos_thermal_print/__init__.py
from . import models
# Wrote custom_addons/pos_thermal_print/models/__init__.py
from . import pos_order
# Wrote custom_addons/pos_thermal_print/models/pos_order.py
# -*- coding: utf-8 -*-
from odoo import models
class PosOrder(models.Model):
    _inherit = 'pos.order'
    def print_thermal_receipt(self):
        return self.print_thermal_receipt()
Thinking: Wait, I'm creating a circular dependency. The pos_thermal_print module depends on pos_kitchen_receipt, which already has the print_thermal_receipt() method on pos.order. So I don't need to add it again in pos_thermal_print/models/pos_order.py.
Let me fix this. The pos_thermal_print module should just add the button to the POS, not duplicate the method.
Actually, I already added print_thermal_receipt() to pos.order in pos_kitchen_receipt/models/pos_order.py. So the pos_thermal_print module doesn't need a models directory at all - it just needs the JS and XML for the button.
Let me remove the models directory from pos_thermal_print and update the init.py.
# Remove models directory from pos_thermal_print
$ rm -rf /home/fasedaff/Documents/odoo-pizzeria/custom_addons/pos_thermal_print/models
(no output)
# Wrote custom_addons/pos_thermal_print/__init__.py
# pos_thermal_print module
Thinking: Now let me create the JS and XML files for the button. I'll follow the pos_takeaway pattern.
The JS file will patch the ReceiptScreen component to add a doThermalPrint method.
The XML file will add a button to the receipt screen template.
# Todos
[✓] 
Add print_thermal_receipt() method to pos.order in pos_kitchen_receipt
[✓] 
Create pos_thermal_print module with button on POS receipt screen
[•] 
Add JS patch for thermal print button (following pos_takeaway pattern)
[ ] 
Add XML template for thermal print button
[ ] 
Test and verify the implementation
Thinking: Now let me create the JS file. I need to patch the ReceiptScreen component to add a doThermalPrint method that calls the print_thermal_receipt method on pos.order via RPC.
# Wrote custom_addons/pos_thermal_print/static/src/js/thermal_print_button.js
/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.doThermalPrint = useTrackedAsync(() => this._printThermalReceipt());
    },
    async _printThermalReceipt() {
        const order = this.currentOrder;
        if (!order) {
            return;
        }
        await this.pos.data.call("pos.order", "print_thermal_receipt", [[order.id]]);
        this.notification.add("Ticket enviado a impresora", { type: "info" });
    },
});
Thinking: Now let me create the XML template. I need to add a button to the receipt screen. Looking at the receipt_screen.xml, I can see there's a section with the print buttons:
<div class="d-flex gap-1">
    <button class="button print btn btn-lg btn-secondary w-100 py-3" t-on-click="() => doFullPrint.call()">
        <i t-attf-class="fa {{doFullPrint.status === 'loading' ? 'fa-fw fa-spin fa-circle-o-notch' : 'fa-print'}} me-1" />Print Full Receipt
    </button>
    <button t-if="pos.config.basic_receipt" class="button print btn btn-lg btn-secondary w-100 py-3" t-on-click="() => doBasicPrint.call()">
        <i t-attf-class="fa {{doBasicPrint.status === 'loading' ? 'fa-fw fa-spin fa-circle-o-notch' : 'fa-print'}} me-1" />Print Basic Receipt
    </button>
</div>
I'll add a button after these that calls doThermalPrint.call().
# Todos
[✓] 
Add print_thermal_receipt() method to pos.order in pos_kitchen_receipt
[✓] 
Create pos_thermal_print module with button on POS receipt screen
[✓] 
Add JS patch for thermal print button (following pos_takeaway pattern)
[•] 
Add XML template for thermal print button
[ ] 
Test and verify the implementation
Thinking: Now let me create the XML template. I'll add a button after the existing print buttons.
# Wrote custom_addons/pos_thermal_print/static/src/xml/thermal_print_button.xml
<?xml version="1.0" encoding="UTF-8"?>
<templates id="template" xml:space="preserve">
    <t t-name="pos_thermal_print.ReceiptScreen" t-inherit="point_of_sale.ReceiptScreen" t-inherit-mode="extension">
        <xpath expr="//button[hasclass('print')][last()]" position="after">
            <button class="button print btn btn-lg btn-secondary w-100 py-3" t-on-click="() => doThermalPrint.call()">
                <i t-attf-class="fa {{doThermalPrint.status === 'loading' ? 'fa-fw fa-spin fa-circle-o-notch' : 'fa-print'}} me-1" />Imprimir Ticket
            </button>
        </xpath>
    </t>
</templates>
Thinking: Now let me install the module and test it.
# Todos
[✓] 
Add print_thermal_receipt() method to pos.order in pos_kitchen_receipt
[✓] 
Create pos_thermal_print module with button on POS receipt screen
[✓] 
Add JS patch for thermal print button (following pos_takeaway pattern)
[✓] 
Add XML template for thermal print button
[•] 
Test and verify the implementation
Thinking: Let me install the module and test it.
# Install pos_thermal_print module
$ docker compose run --rm web odoo -c /etc/odoo/odoo.conf -d elgordo -i pos_thermal_print --stop-after-init 2>&1 | tail -30
Container pizzeria-db-1 Running 
 Container pizzeria-web-run-1f104f3c926f Creating 
 Container pizzeria-web-run-1f104f3c926f Created 
2026-06-13 16:25:02,538 1 WARNING ? odoo.tools.config: option addons_path, invalid addons directory '/mnt/extra-addons', skipped 
2026-06-13 16:25:02,538 1 WARNING ? odoo.tools.config: option addons_path, invalid addons directory '/mnt/extra-addons', skipped 
2026-06-13 16:25:02,538 1 WARNING ? odoo.tools.config: missing --http-interface/http_interface, using 0.0.0.0 by default, will change to 127.0.0.1 in 20.0 
2026-06-13 16:25:02,538 1 INFO ? odoo: Odoo version 19.0-20260421 
2026-06-13 16:25:02,538 1 INFO ? odoo: Using configuration file at /etc/odoo/odoo.conf 
2026-06-13 16:25:02,539 1 INFO ? odoo: addons paths: _NamespacePath(['/usr/lib/python3/dist-packages/odoo/addons', '/var/lib/odoo/.local/share/Odoo/addons/19.0', '/mnt/custom-addons', '/usr/lib/python3/dist-packages/addons']) 
2026-06-13 16:25:02,539 1 INFO ? odoo: database: odoo@db:5432 
…
Click to expand
Thinking: Module installed successfully. Now let me restart the web container and verify everything is working.
# Restart web container
$ docker compose restart web
Container pizzeria-web-1 Restarting 
 Container pizzeria-web-1 Started
Thinking: Now let me also remove the old receipt_print.js from pos_kitchen_screen_odoo since we're using the new module instead. And I should also remove the print_customer_receipt method from pos_kitchen_screen_odoo/models/pos_orders.py since we now have print_thermal_receipt in pos_kitchen_receipt.
Actually, let me check what's in pos_kitchen_screen_odoo first.
→ Read custom_addons/pos_kitchen_screen_odoo/static/src/js/receipt_print.js 
→ Read custom_addons/pos_kitchen_screen_odoo/models/pos_orders.py 
Thinking: I see that the old implementation in pos_kitchen_screen_odoo has:
1. receipt_print.js - patches PosStore.printReceipt() to call print_customer_receipt
2. print_customer_receipt() method in pos_orders.py
Now I have the new implementation in pos_kitchen_receipt and pos_thermal_print:
1. print_thermal_receipt() method in pos_kitchen_receipt/models/pos_order.py
2. pos_thermal_print module with button on receipt screen
I should remove the old implementation to avoid conflicts. Let me:
1. Remove receipt_print.js from pos_kitchen_screen_odoo
2. Remove the print_customer_receipt method from pos_kitchen_screen_odoo/models/pos_orders.py
3. Remove the reference to receipt_print.js from the manifest
# Remove old receipt_print.js
$ rm /home/fasedaff/Documents/odoo-pizzeria/custom_addons/pos_kitchen_screen_odoo/static/src/js/receipt_print.js
(no output)
← Edit custom_addons/pos_kitchen_screen_odoo/models/pos_orders.py
    if not pos_order:
        return False
    tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(pos_order)
    return [t.id for t in tickets] if tickets else False
def print_customer_receipt(self):
    self.ensure_one()
    ticket = self.env["pos.kitchen.ticket"].search([
        ("origin_pos_order_id", "=", self.id),
        ("ticket_type", "=", "new"),
    ], limit=1)
    if not ticket:
        ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(self)
    if ticket:
        return ticket.print_ticket()
    return False
→ Read custom_addons/pos_kitchen_screen_odoo/__manifest__.py 
Thinking: I need to remove the reference to receipt_print.js from the manifest since I deleted that file.
← Edit custom_addons/pos_kitchen_screen_odoo/__manifest__.py
        'pos_kitchen_screen_odoo/static/src/js/order_button.js',
        'pos_kitchen_screen_odoo/static/src/js/order_pay.js',
        'pos_kitchen_screen_odoo/static/src/js/order_model.js',
        'pos_kitchen_screen_odoo/static/src/js/order_type_buttons.js',
        'pos_kitchen_screen_odoo/static/src/js/receipt_print.js',
        'pos_kitchen_screen_odoo/static/src/xml/order_type_buttons.xml',
    ],
},
'images': [
Thinking: Now let me also add the new module to the nuclear-reset script so it gets installed on fresh resets.
→ Read scripts/nuclear-reset.sh 
Thinking: I need to add pos_thermal_print to both install commands in nuclear-reset.sh.
← Edit scripts/nuclear-reset.sh
echo ""
echo "[0/3] Ensuring custom modules are installed..."
docker compose run --rm web odoo -c /etc/odoo/odoo.conf -d elgordo \
  -i pos_hr,pos_kitchen_screen_odoo,pos_receipt_logo,pos_kitchen_receipt,pos_takeaway,pos_ticket_status --stop-after-init
  -i pos_hr,pos_kitchen_screen_odoo,pos_receipt_logo,pos_kitchen_receipt,pos_takeaway,pos_ticket_status,pos_thermal_print --stop-after-init
echo ""
echo "[1/3] Cleaning existing data..."
"$SCRIPT_DIR/clean-data.sh"
← Edit scripts/nuclear-reset.sh
docker compose up -d
echo "  Waiting for database to be ready (20s)..."
sleep 20
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i base,stock,mrp,point_of_sale,pos_restaurant,pos_hr,pos_kitchen_screen_odoo,pos_receipt_logo,pos_kitchen_receipt,pos_takeaway,pos_ticket_status --stop-after-init
  -i base,stock,mrp,point_of_sale,pos_restaurant,pos_hr,pos_kitchen_screen_odoo,pos_receipt_logo,pos_kitchen_receipt,pos_takeaway,pos_ticket_status,pos_thermal_print --stop-after-init
echo ""
echo "[2/3] Importing all data..."
"$SCRIPT_DIR/import-data.sh"