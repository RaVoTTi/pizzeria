Implementation Plan
Phase 1: Add order_type field to KDS ticket model
File: custom_addons/pos_kitchen_screen_odoo/models/pos_kitchen_ticket.py
1. 
Add computed order_type selection field (mesa, delivery, retira) on pos.kitchen.ticket
2. 
Compute logic:
- 
table_id → mesa
- 
No table + partner_id.street → delivery
- 
No table + no street → retira
3. 
Update get_details() to include order_type in JS payload
Phase 2: Update KDS frontend to use order_type
File: custom_addons/pos_kitchen_screen_odoo/static/src/js/kitchen_screen.js
- 
Update getTicketType() to return the server-computed order_type
File: custom_addons/pos_kitchen_screen_odoo/static/src/xml/kitchen_screen_templates.xml
- 
Replace the fragile ticketType === 'mesa' / partner_name heuristic with ticket.order_type
Phase 3: Update ticket printer to use order_type
File: custom_addons/pos_kitchen_receipt/models/ticket_printer.py
- 
Use ticket.order_type for MESA/DELIVERY/RETIRA labels
- 
Use ticket.order_type for pizza section headers (PIZZAS SALON / PIZZAS DELIVERY / PIZZAS RETIRA)
- 
Only print address when order_type == 'delivery'
Phase 4: Manual time picker for requested_time
File: custom_addons/pos_kitchen_screen_odoo/models/pos_kitchen_ticket.py
- 
Add requested_time field to pos.order (or use existing if present)
- 
In get_or_create_ticket(), copy requested_time from pos.order to ticket
File: POS order form view (need to check existing views)
- 
Add a datetime picker widget for requested_time on the POS order screen

pos.order (Standard Odoo 19 fields, no custom fields added yet)
Field	Type	Notes
config_id	Many2one(pos.config)	Standard
session_id	Many2one(pos.session)	Standard
partner_id	Many2one(res.partner)	Standard
table_id	Many2one(restaurant.table)	From pos_restaurant
pos_reference	Char	Standard
name	Char	Standard
state	Selection	Standard
lines	One2many(pos.order.line)	Standard
amount_total	Monetary	Standard
general_customer_note	Text	Standard Odoo 19
pos.order.line — Custom field added
Field	Type	Notes
qty_sent_to_kitchen	Float	Tracks qty already sent to kitchen (for delta detection)
pos.kitchen.ticket — 17 fields already defined
Field	Type	Notes
origin_pos_order_id	Many2one(pos.order)	Required
pos_config_id	Many2one(pos.config)	Related, stored
pos_reference	Char	Related, stored
order_name	Char	Related, stored
table_id	Many2one(restaurant.table)	Related, stored
partner_id	Many2one(res.partner)	Related, stored
session_id	Many2one(pos.session)	Related, stored
sequence	Char	Auto-generated (KT-0001)
batch_letter	Char(1)	A=original, B/C/D=modifications
ticket_type	Selection	new/addition/cancellation/modification
state	Selection	pending/cooking/waiting/ready/delivered/cancelled
payment_status	Selection	paid/not_paid
line_ids	One2many	Ticket lines
started_at	Datetime	Cooking start time
ready_at	Datetime	Ready time
delivered_at	Datetime	Delivery time
requested_time	Datetime	Customer desired time (exists but never set)
pos.kitchen.ticket.line — 11 fields
Field	Type	Notes
ticket_id	Many2one	Parent ticket
pos_order_line_id	Many2one	Source POS line
product_id	Many2one	Related, stored
full_product_name	Char	Related, stored
note	Char	Extracted from JSON
product_category	Char	Pizza/Empanada/Bebida/Envio/Otro
qty_total	Float	 
qty_sent	Float	 
qty_ready	Float	 
qty_cancelled	Float	 
state	Selection	pending/cooking/waiting/ready/cancelled
Safe to Add (no conflicts)
Model	Field	Type	Purpose
pos.order	requested_time	Datetime	Manual time picker for customer desired time
pos.kitchen.ticket	order_type	Selection (mesa/delivery/retira)	Computed field for reliable order classification

KDS Objects & Structure
Backend Models (Python)
Model	File
kitchen.screen	kitchen_screen.py
pos.kitchen.ticket	pos_kitchen_ticket.py
pos.kitchen.ticket.line	pos_kitchen_ticket.py
kitchen.ticket.printer	ticket_printer.py (receipt module)
Frontend (OWL Component)
KitchenScreenDashboard (kitchen_screen.js)
- 
Registered as client action kitchen_custom_dashboard_tags
- 
Uses useState for reactive state: tickets, sortedTickets, stages, ovenCapacity, etc.
- 
Services: orm (RPC), bus_service (real-time), notification (toasts)
Event System (bus.bus — Odoo Longpolling)
Channel: pos_kitchen.<pos_config_id>
All events trigger the same action: loadTickets() — full data refresh
Event	Triggered By
pos_order_created	New ticket created (order or delta)
pos_order_paid	Payment completed
pos_order_accepted	Ticket → cooking
pos_order_completed	Ticket → ready
pos_order_delivered	Ticket → delivered
pos_order_cancelled	Ticket cancelled
pos_order_line_cooking	Line → cooking
pos_order_line_ready	Line → ready
pos_order_line_cancelled	Line cancelled
pos_order_line_updated	Line toggled
Fallback: 30-second setInterval polling masks any bus channel issues.
Data Flow
1. Order Creation
POS → pos.order.create() → get_or_create_ticket() → pos.kitchen.ticket
  → bus notification → KDS loadTickets() → renders new card + chime
2. Order Modification
POS → processOrderForKitchen() RPC → create_delta_tickets()
  → compares qty vs qty_sent_to_kitchen
  → delta > 0: "addition" ticket (batch B/C/D)
  → delta < 0: "cancellation" ticket
  → bus notification → KDS reloads
3. State Progression (tap card)
KDS tap → optimistic UI update → RPC progress_to_cooking/ready/delivered()
  → validates state transition → sets timestamps → bus notification → all KDS reload
4. Print
KDS "Imprimir" → RPC print_ticket() → kitchen.ticket.printer.format_ticket_escpos()
  → appends logo bytes → subprocess lp -d <printer> -o raw → CUPS prints
State Machines
Ticket: pending → cooking → ready → delivered (or cancelled from any)
Line: pending → cooking → ready → cancelled → pending (cycles on toggle)
Auto-sync: When all lines are ready, ticket auto-advances to ready.
How Order Type Is Currently Determined
No explicit field — derived from table_id + partner_id.street:
Condition	Result
table_id exists	Mesa
No table + partner_id.street exists	Delivery
No table + no street	Retira
This logic is duplicated in:
- 
kitchen_screen.js:139 (getTicketType() — only returns 'mesa' or 'delivery')
- 
kitchen_screen_templates.xml:111-153 (template heuristic)
- 
ticket_printer.py:44-49 (printer labels)