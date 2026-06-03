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

Your plan is solid in direction, but there are a few structural problems that will bite you later if you implement it exactly like this. Let’s go through it critically and tighten it so it’s actually production-safe.

---

# 🔴 The main issues (before phases)

### 1. ❌ You’re mixing **business logic with weak heuristics**

This rule:

* `No table + partner.street → delivery`

…is fragile.

Real-world problems:

* A customer can have an address but still **pick up**
* A delivery might not have `street` filled yet
* POS users might reuse partners

👉 **Better approach:**
If possible, define `order_type` at the **POS order level explicitly**, not inferred.

If you *must infer*, at least prioritize something like:

```python
if order.is_delivery_flag:
    return 'delivery'
```

---

### 2. ❌ You're computing `order_type` on the ticket instead of the source

You’re putting logic in `pos.kitchen.ticket`, but:

👉 That model is **derived / append-only**, not the source of truth.

So:

* Logic duplication risk
* Harder debugging
* Future inconsistencies

👉 **Correct architecture:**

* Compute/store `order_type` in `pos.order`
* Copy it into the ticket

---

### 3. ❌ `requested_time` on ticket is wrong ownership

Same issue:

👉 `requested_time` belongs to the **order**, not the ticket.

Tickets are just a *projection*.

---

# ✅ Improved Implementation Plan (clean version)

---

## 🟢 Phase 1 — Fix the data model (DO THIS FIRST)

### File: `pos_order.py`

Add:

```python
order_type = fields.Selection([
    ('mesa', 'Mesa'),
    ('delivery', 'Delivery'),
    ('retira', 'Retira'),
], default='mesa', required=True)

requested_time = fields.Datetime(string="Hora solicitada")
```

👉 Optional fallback compute:

```python
@api.onchange('table_id', 'partner_id')
def _onchange_order_type(self):
    for order in self:
        if order.table_id:
            order.order_type = 'mesa'
        elif order.partner_id and order.partner_id.street:
            order.order_type = 'delivery'
        else:
            order.order_type = 'retira'
```

---

## 🟢 Phase 2 — Propagate to ticket (correct place)

### File: `pos_kitchen_ticket.py`

Add **stored fields (NOT computed):**

```python
order_type = fields.Selection([...])
requested_time = fields.Datetime()
```

### In `get_or_create_ticket()`:

```python
ticket.order_type = order.order_type
ticket.requested_time = order.requested_time
```

👉 This ensures:

* Tickets are snapshots
* No recompute inconsistencies

---

## 🟢 Phase 3 — Backend → Frontend payload

### In `get_details()`:

```python
'order_type': self.order_type,
'requested_time': self.requested_time,
```

---

## 🟢 Phase 4 — Frontend cleanup (GOOD idea, but simplify more)

### JS: `kitchen_screen.js`

Replace:

```js
getTicketType()
```

With:

```js
ticket.order_type
```

👉 Delete heuristics entirely. No fallback logic.

---

### XML: `kitchen_screen_templates.xml`

Replace ALL this kind of logic:

```xml
t-if="ticketType === 'mesa'"
```

With:

```xml
t-if="ticket.order_type === 'mesa'"
```

👉 This is exactly the kind of cleanup that makes KDS stable 👍

---

## 🟢 Phase 5 — Printer (this is where it matters most)

### File: `ticket_printer.py`

Use:

```python
if ticket.order_type == 'mesa':
    label = 'MESA'
elif ticket.order_type == 'delivery':
    label = 'DELIVERY'
else:
    label = 'RETIRA'
```

### Pizza headers:

```python
PIZZAS SALON
PIZZAS DELIVERY
PIZZAS RETIRA
```

---

### Address rule (correct 👍):

```python
if ticket.order_type == 'delivery':
    print(address)
```

---

## 🟢 Phase 6 — POS UI (this is your missing piece)

Right now your plan says:

> “need to check existing views”

That’s not optional — it’s **critical**.

👉 If the user can’t SELECT order type, your whole system is guesswork.

### You need:

* A selector:

  * Mesa
  * Delivery
  * Retira

OR:

* Buttons (better UX for POS)

---

# 🔴 Big missing piece in your plan

## ❗ You didn’t define how the user sets `order_type`

Without this:

* Your logic = unreliable
* Staff will fight the system
* Tickets will be wrong

---

# 💡 Final architecture (clean mental model)

```
POS UI  →  pos.order  →  pos.kitchen.ticket  →  KDS / Printer
           (source)       (snapshot)
```

---

# 🧠 Summary (brutally honest)

What you proposed:

* ✔ Good direction
* ❌ Wrong ownership (ticket vs order)
* ❌ Fragile inference logic
* ❌ Missing UI control

What you should do:

* Move logic to `pos.order`
* Store values (don’t compute on ticket)
* Kill all frontend heuristics
* Add explicit POS control

---

If you want, next step I can:

* Design the **exact POS UI (buttons layout)**
* Or write the **full Odoo code for each phase (copy-paste ready)**


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


Here's the KDS architecture breakdown:
KDS Objects & Structure
Backend Models (Python)
Model	File	Purpose
kitchen.screen	kitchen_screen.py	Config: POS link, categories, printer name, oven capacity
pos.kitchen.ticket	pos_kitchen_ticket.py	Core ticket: state machine, lines, times, payment status
pos.kitchen.ticket.line	pos_kitchen_ticket.py	Individual product lines with their own state
kitchen.ticket.printer	ticket_printer.py (receipt module)	AbstractModel for ESC/POS formatting + CUPS printing
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


Short answer: **not automatically**. Installing a Cybrosys addon does **not** make your system more stable by default. It can *help*, but only if you use it the right way.

Let’s be precise about this.

---

# 🧠 The misconception

> “If I use Cybrosys instead of my own UI, it will be more stable”

That’s only true for:

* basic UI interactions
* standard POS behaviors

It is **NOT true** for:

* custom KDS flows
* kitchen routing
* ticket printing logic

---

# ⚖️ Reality: stability comparison

## Option A — Your own implementation

**Pros**

* Full control
* Clean architecture
* No external dependency

**Cons**

* You must build UI
* More initial effort
* You must maintain it

---

## Option B — Using Cybrosys addon

**Pros**

* Ready-made POS UI (big win)
* Faster to implement
* Already tested in general cases

**Cons (important)**

* You depend on their model design
* Updates can break things
* Not designed for *your* KDS logic
* Hidden assumptions (this is the dangerous part)

---

# 🔴 Where Cybrosys WILL break (if you’re not careful)

Typical issues:

* Field names change between versions
* JS behavior overridden unexpectedly
* Order type logic tied to UI assumptions
* No clear separation between:

  * dine-in
  * takeaway
  * delivery

👉 And your system is **not generic POS** — it's a **kitchen system**, which is stricter.

---

# ✅ The correct strategy (hybrid approach)

What you *should* do:

```text
Use Cybrosys for:
✔ UI (buttons in POS)
✔ User interaction

Use YOUR code for:
✔ Business logic
✔ order_type normalization
✔ KDS behavior
✔ Printer behavior
```

---

# 🧱 Think of Cybrosys as a UI layer only

```text
[ Cybrosys UI ]
        ↓
pos.order.order_type_id   (external)
        ↓
pos.order.order_type      (your normalized field ✅)
        ↓
pos.kitchen.ticket        (your system ✅)
        ↓
KDS / Printer             (your system ✅)
```

👉 Stability comes from **this separation**, not from the addon itself.

---

# 🔥 Key insight (this is the important part)

If you:

* ❌ rely directly on `order_type_id.name`
* ❌ use their logic inside KDS
* ❌ skip normalization

Then Cybrosys will actually make your system **LESS stable**, not more.

---

# 🟢 When Cybrosys DOES improve stability

Only in this case:

* You **don’t reinvent the POS UI**
* You **don’t depend on their internal logic**
* You **map their data into your own controlled model**

Then you get:

* faster development
* fewer UI bugs
* consistent cashier workflow

---

# 🧠 My honest recommendation

For your case (KDS + tickets + pizza logic):

👉 Yes, use Cybrosys
👉 But treat it as a **UI plugin, not a core system**

---

# 💬 If I were implementing your system

I would:

1. Install Cybrosys `pos_order_types`
2. Add a `code` field (mesa/delivery/retira)
3. Normalize into `pos.order.order_type`
4. Completely ignore Cybrosys in:

   * KDS
   * printer
5. Never use heuristics again

---

# 🧩 Final takeaway

> Stability doesn’t come from *who wrote the code*
> It comes from **who owns the logic**

* If Cybrosys owns it → unstable for your use case
* If YOU own it → stable

---

If you want, I can:

* Show you the **exact minimal patch to Cybrosys** (no fork, upgrade-safe)
* Or design a **clean POS UI alternative that’s even simpler than Cybrosys**
