# Implementation Plan: Order Type Normalization (mesa/delivery/retira)

## Goal

Replace fragile heuristic-based order type detection (table_id + partner.street) with an explicit, user-selected `order_type` field that flows through the entire system:

```
POS UI → pos.order (source) → pos.kitchen.ticket (snapshot) → KDS / Printer
```

## Current State

### Modules involved

| Module | Version | Role |
|--------|---------|------|
| `pos_takeaway` | v18 (Cybrosys) | Binary dine-in/takeaway toggle in POS |
| `pos_kitchen_screen_odoo` | v18 (Cybrosys, heavily customized) | KDS + ticket model |
| `pos_kitchen_receipt` | v19 (custom) | ESC/POS printer formatting |
| `pos_receipt_logo` | v19 (custom) | Logo on receipts |

### Current heuristic (duplicated in 3 places)

```
table_id exists?           → MESA
no table + partner.street? → DELIVERY
no table + no street?      → RETIRA
```

Locations:
- `kitchen_screen.js:139` — `getTicketType()` (only returns mesa/delivery, no retira!)
- `kitchen_screen_templates.xml:144-153` — three-way via partner_name fallback
- `ticket_printer.py:44-49` and `100-107` — MESA/DELIVERY/RETIRA + pizza headers

### pos_takeaway v18 compatibility issues

1. **Import path mismatch**: `ReceiptScreen.js` imports from `@point_of_sale/app/store/pos_store` (v18) — v19 uses `@point_of_sale/app/services/pos_store` (confirmed by Docker exploration)
2. **Import path mismatch**: `TakeAwayButton.js` imports `usePos` from `@point_of_sale/app/store/pos_hook` — v19 equivalent is direct service injection via `useService("orm")` (same pattern as `order_button.js` in the KDS module)
3. **Missing `buttonClass` getter**: `TakeAwayButton.xml` references `buttonClass` but the JS manipulates `this.TakeAway.el.className` directly — `buttonClass` is undefined
4. **Duplicate filter name**: `pos_order_view.xml` has two `<filter>` elements both named `take_away`
5. **Binary model**: Only `is_takeaway`/`is_dine_in` booleans — cannot distinguish delivery vs retira
6. **Manifest version**: Still `18.0.1.0.0`

---

## Phase 0 — Fix pos_takeaway v18→v19 compatibility

**Why first**: The module currently may not load correctly in Odoo 19. Fix before adding new logic.

### 0.1 Fix JS import paths

**File**: `custom_addons/pos_takeaway/static/src/js/Screens/ProductScreen/ReceiptScreen/ReceiptScreen.js`

Change:
```js
import { PosStore } from "@point_of_sale/app/store/pos_store";
```
To:
```js
import { PosStore } from "@point_of_sale/app/services/pos_store";
```

**File**: `custom_addons/pos_takeaway/static/src/js/Screens/ProductScreen/ControlButton/TakeAwayButton.js`

Verify `usePos` import path works in v19. If `@point_of_sale/app/store/pos_hook` doesn't exist, replace with direct service injection (same pattern as `order_button.js` in the KDS module).

### 0.2 Fix missing `buttonClass` getter

**File**: `custom_addons/pos_takeaway/static/src/js/Screens/ProductScreen/ControlButton/TakeAwayButton.js`

Add a `buttonClass` getter to the patch:
```js
get buttonClass() {
    const order = this.pos.get_order();
    if (order && order.is_takeaway) {
        return "control-button customer-button btn rounded-0 fw-bolder text-truncate btn-primary";
    }
    return "control-button btn btn-light rounded-0 fw-bolder";
}
```

Remove the direct `this.TakeAway.el.className` manipulation from `onClick()` — let the reactive getter handle it.

### 0.3 Fix duplicate filter name

**File**: `custom_addons/pos_takeaway/views/pos_order_view.xml`

Change:
```xml
<filter string="Dine In" name="take_away" .../>
<filter string="Take Away" name="take_away" .../>
```
To:
```xml
<filter string="Dine In" name="dine_in" domain="[('is_takeaway','=', False)]"/>
<filter string="Take Away" name="take_away" domain="[('is_takeaway','=', True)]"/>
```

### 0.4 Update manifest version

**File**: `custom_addons/pos_takeaway/__manifest__.py`

Change `'version': '18.0.1.0.0'` to `'version': '19.0.1.0.0'`

### 0.5 Verify and test

- Restart Odoo, confirm module loads without errors
- Open POS, verify Take Away button renders and toggles
- Verify receipt header shows Dine-In / Take Away correctly

---

## Phase 1 — Add `order_type` + `requested_time` to `pos.order` (source of truth)

### 1.1 Add fields to pos.order

**File**: `custom_addons/pos_kitchen_screen_odoo/models/pos_orders.py`

Add:
```python
order_type = fields.Selection([
    ('mesa', 'Mesa'),
    ('delivery', 'Delivery'),
    ('retira', 'Retira'),
], string="Tipo de Orden", default='mesa', required=True)

requested_time = fields.Datetime(string="Hora Solicitada")
```

### 1.2 Add onchange for auto-suggestion (backend only)

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

This is a **suggestion only** — the POS UI (Phase 6) is the authoritative setter.

### 1.3 Add backend view for pos.order

**File**: `custom_addons/pos_kitchen_screen_odoo/views/pos_order_views.xml` (currently empty)

Add `order_type` and `requested_time` fields to the pos.order form view (inherit from `point_of_sale.view_pos_pos_form`):
```xml
<record id="view_pos_order_form_kitchen" model="ir.ui.view">
    <field name="name">pos.order.form.kitchen</field>
    <field name="model">pos.order</field>
    <field name="inherit_id" ref="point_of_sale.view_pos_pos_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='partner_id']" position="after">
            <field name="order_type"/>
            <field name="requested_time" widget="datetime"/>
        </xpath>
    </field>
</record>
```

### 1.4 POS frontend data loading (automatic in v19)

**No code needed.** In Odoo 19, `pos.order` has no `_load_pos_data_fields` override, which means it returns `[]` (empty list). The POS data loading pipeline interprets this as "load ALL fields". The frontend auto-generates getter/setter properties for every field in the schema.

This is the same mechanism that makes `pos_restaurant`'s `table_id` work without any JS serialization code.

**Contrast with `pos.order.line`**: That model DOES have an explicit field list, which is why `qty_sent_to_kitchen` needs a `_load_pos_data_fields` override. But `pos.order` fields are auto-loaded.

### 1.5 Add pos.order tree/list view column

Add `order_type` to the pos.order tree view for easy backend filtering.

---

## Phase 2 — Propagate `order_type` to `pos.kitchen.ticket` (snapshot)

### 2.1 Add stored field on ticket

**File**: `custom_addons/pos_kitchen_screen_odoo/models/pos_kitchen_ticket.py`

Add (NOT related, NOT computed — stored snapshot):
```python
order_type = fields.Selection([
    ('mesa', 'Mesa'),
    ('delivery', 'Delivery'),
    ('retira', 'Retira'),
], string="Tipo de Orden")
```

Note: `requested_time` already exists on the ticket model (line 103-105). It just needs to be populated.

### 2.2 Copy values in `get_or_create_ticket()`

**File**: `custom_addons/pos_kitchen_screen_odoo/models/pos_kitchen_ticket.py` (line 338-344)

In the `self.create({...})` call, add:
```python
"order_type": pos_order.order_type,
"requested_time": pos_order.requested_time,
```

### 2.3 Copy values in `create_delta_tickets()`

**File**: `custom_addons/pos_kitchen_screen_odoo/models/pos_kitchen_ticket.py` (lines 412-419, 439-446)

In both the addition and cancellation `self.create({...})` calls, add:
```python
"order_type": pos_order.order_type,
"requested_time": pos_order.requested_time,
```

### 2.4 Immutability rule

Once a ticket is created, `order_type` is **frozen**. If the cashier changes `order_type` on the POS order after tickets exist:
- Existing tickets keep their original `order_type`
- New delta tickets get the updated `order_type`
- This is consistent with how the batch system already works

---

## Phase 3 — Update `get_details()` payload

### 3.1 Add `order_type` to ticket dict

**File**: `custom_addons/pos_kitchen_screen_odoo/models/pos_kitchen_ticket.py` (line 286-304)

In the `result.append({...})` dict, add:
```python
"order_type": ticket.order_type or "mesa",
```

The `requested_time` is already included (line 300).

---

## Phase 4 — Update KDS frontend (kill heuristics)

### 4.1 Replace `getTicketType()` in JS

**File**: `custom_addons/pos_kitchen_screen_odoo/static/src/js/kitchen_screen.js` (line 139-141)

Replace:
```js
getTicketType(ticket) {
    return ticket.table_id ? 'mesa' : 'delivery';
}
```
With:
```js
getTicketType(ticket) {
    return ticket.order_type || 'mesa';
}
```

### 4.2 Update XML template — order type badge

**File**: `custom_addons/pos_kitchen_screen_odoo/static/src/xml/kitchen_screen_templates.xml` (lines 144-153)

Replace:
```xml
<t t-if="ticketType === 'mesa'">
    <span class="kds-type-badge kds-type-mesa">MESA</span>
</t>
<t t-elif="ticket.partner_name">
    <span class="kds-type-badge kds-type-delivery">DELIVERY</span>
</t>
<t t-else="">
    <span class="kds-type-badge kds-type-pickup">RETIRO</span>
</t>
```
With:
```xml
<t t-if="ticket.order_type === 'mesa'">
    <span class="kds-type-badge kds-type-mesa">MESA</span>
</t>
<t t-elif="ticket.order_type === 'delivery'">
    <span class="kds-type-badge kds-type-delivery">DELIVERY</span>
</t>
<t t-else="">
    <span class="kds-type-badge kds-type-pickup">RETIRO</span>
</t>
```

### 4.3 Update XML template — header identity row

**File**: `custom_addons/pos_kitchen_screen_odoo/static/src/xml/kitchen_screen_templates.xml` (lines 111-119)

Replace:
```xml
<t t-if="partner">
    <span class="kds-customer-name"><t t-esc="partner"/></span>
</t>
<t t-elif="ticketType === 'mesa'">
    <span class="kds-customer-name">MESA <t t-esc="ticket.table_name"/></span>
</t>
<t t-else="">
    <span class="kds-customer-name">RETIRO</span>
</t>
```
With:
```xml
<t t-if="ticket.order_type === 'mesa'">
    <span class="kds-customer-name">MESA <t t-esc="ticket.table_name"/></span>
</t>
<t t-elif="partner">
    <span class="kds-customer-name"><t t-esc="partner"/></span>
</t>
<t t-else="">
    <span class="kds-customer-name">RETIRO</span>
</t>
```

This fixes the current bug where mesa orders with a partner show the partner name instead of the table number.

---

## Phase 5 — Update ticket printer (use `order_type`)

### 5.1 Replace MESA/DELIVERY/RETIRA label logic

**File**: `custom_addons/pos_kitchen_receipt/models/ticket_printer.py` (lines 43-49)

Replace:
```python
if ticket.table_id:
    lines.append(f"{DBLHW}MESA {ticket.table_id.table_number}{NORM}")
elif ticket.partner_id and ticket.partner_id.street:
    type_parts.append("DELIVERY")
else:
    type_parts.append("RETIRA")
```
With:
```python
if ticket.order_type == 'mesa':
    table_num = ticket.table_id.table_number if ticket.table_id else "?"
    lines.append(f"{DBLHW}MESA {table_num}{NORM}")
elif ticket.order_type == 'delivery':
    type_parts.append("DELIVERY")
else:
    type_parts.append("RETIRA")
```

### 5.2 Replace pizza section header logic

**File**: `custom_addons/pos_kitchen_receipt/models/ticket_printer.py` (lines 100-107)

Replace:
```python
if ticket.table_id:
    pizza_label = "PIZZAS SALON"
elif ticket.partner_id and ticket.partner_id.street:
    pizza_label = "PIZZAS DELIVERY"
else:
    pizza_label = "PIZZAS RETIRA"
```
With:
```python
pizza_labels = {
    'mesa': "PIZZAS SALON",
    'delivery': "PIZZAS DELIVERY",
    'retira': "PIZZAS RETIRA",
}
pizza_label = pizza_labels.get(ticket.order_type, "PIZZAS SALON")
```

### 5.3 Fix address printing — only for delivery, with edge cases

**File**: `custom_addons/pos_kitchen_receipt/models/ticket_printer.py` (lines 147-151)

Replace:
```python
if ticket.partner_id and ticket.partner_id.street:
    lines.append(DIVIDER)
    lines.append(f"{DBLH}  {ticket.partner_id.street}{NORM}")
    if ticket.partner_id.street2:
        lines.append(f"{DBLH}  {ticket.partner_id.street2}{NORM}")
```
With:
```python
if ticket.order_type == 'delivery' and ticket.partner_id:
    street = (ticket.partner_id.street or "").strip()
    street2 = (ticket.partner_id.street2 or "").strip()
    if street:
        lines.append(DIVIDER)
        lines.append(f"{DBLH}  {street[:38]}{NORM}")
        if street2:
            lines.append(f"{DBLH}  {street2[:38]}{NORM}")
    else:
        lines.append(DIVIDER)
        lines.append(f"{BOLD}  VER DIRECCION EN SISTEMA{NORM}")
```

### 5.4 Add fallback for legacy tickets

For tickets created before this migration (no `order_type` set), add a fallback at the top of `format_ticket_escpos()`:
```python
order_type = ticket.order_type
if not order_type:
    if ticket.table_id:
        order_type = 'mesa'
    elif ticket.partner_id and ticket.partner_id.street:
        order_type = 'delivery'
    else:
        order_type = 'retira'
```

Then use `order_type` variable throughout instead of `ticket.order_type`.

---

## Phase 6 — POS UI: Three-state order type selector

### 6.0 POS data persistence (CRITICAL — must be done before buttons)

**Why this matters**: Setting `order.order_type = 'delivery'` in JS memory is useless if the value is silently dropped when the POS syncs the order to the backend. Without this step, the backend defaults to `mesa` for every order, making the entire system produce wrong tickets.

**How Odoo 19 handles this**: The old `export_as_JSON()` / `init_from_JSON()` methods (Odoo ≤18) no longer exist. In v19:

- `PosOrder` extends `PosOrderAccounting` (at `@point_of_sale/app/models/pos_order`)
- Serialization uses `serializeForORM()` which auto-iterates all fields in the model definition
- Since `pos.order` loads ALL fields (see Phase 1.4), any Python field is **automatically available** in the frontend with auto-generated getter/setter
- The field is **automatically serialized** back to the backend on sync

**What we need**: A minimal JS patch on `PosOrder.prototype` to set defaults. No serialization override needed.

**File**: `custom_addons/pos_kitchen_screen_odoo/static/src/js/order_model.js` (new file)

```js
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        if (!this.order_type) {
            this.order_type = this.table_id ? 'mesa' : null;
        }
    },
});
```

**Why this is enough**:
1. Python field `order_type` is auto-loaded into POS schema (Phase 1.4)
2. Frontend auto-generates `order.order_type` getter/setter
3. `serializeForORM` auto-includes it in the RPC payload
4. Backend `pos.order.create()` receives it
5. `get_or_create_ticket()` copies it to ticket (Phase 2)

**The full data flow**:
```
POS button click → order.order_type = 'delivery'
    ↓
pos.syncAllOrders() → serializeForORM() → RPC payload includes order_type
    ↓
backend pos.order.create(order_type='delivery')
    ↓
get_or_create_ticket() → ticket.order_type = 'delivery'
    ↓
KDS loadTickets() → ticket.order_type === 'delivery'
    ↓
printer → DELIVERY label
```

### 6.1 Design decisions

- **Buttons** (not dropdown) — faster for POS touchscreens
- **Default**: `mesa` when a table is selected, otherwise no default (must select)
- **Visual**: Three large buttons with distinct colors:
  - MESA (blue) — `fa-cutlery` icon
  - DELIVERY (orange) — `fa-motorcycle` icon
  - RETIRA (gray) — `fa-shopping-bag` icon
- **Position**: In the control buttons area, near the partner selector
- **Behavior**: Mutually exclusive — selecting one deselects others

### 6.2 Create new POS JS component

**File**: `custom_addons/pos_kitchen_screen_odoo/static/src/js/order_type_buttons.js`

Create a new OWL component that patches `ControlButtons` (same pattern as TakeAwayButton.js but with three states):

```js
patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
    },

    get currentOrderType() {
        const order = this.pos.getOrder();
        return order?.order_type || 'mesa';
    },

    get mesaClass() {
        return this.currentOrderType === 'mesa'
            ? 'control-button btn btn-primary rounded-0 fw-bolder'
            : 'control-button btn btn-light rounded-0 fw-bolder';
    },

    get deliveryClass() {
        return this.currentOrderType === 'delivery'
            ? 'control-button btn btn-warning rounded-0 fw-bolder'
            : 'control-button btn btn-light rounded-0 fw-bolder';
    },

    get retiraClass() {
        return this.currentOrderType === 'retira'
            ? 'control-button btn btn-secondary rounded-0 fw-bolder'
            : 'control-button btn btn-light rounded-0 fw-bolder';
    },

    setOrderType(type) {
        const order = this.pos.getOrder();
        if (order) {
            order.order_type = type;
        }
    },
});
```

### 6.3 Create OWL template

**File**: `custom_addons/pos_kitchen_screen_odoo/static/src/xml/order_type_buttons.xml`

Extend `point_of_sale.ControlButtons` to add three buttons after the partner selector.

### 6.4 Register assets

**File**: `custom_addons/pos_kitchen_screen_odoo/__manifest__.py`

Add the new JS and XML files to the `point_of_sale._assets_pos` asset bundle.

### 6.5 Auto-default when table is selected

When a table is selected in the POS floor plan, automatically set `order_type = 'mesa'`. This happens naturally since `pos_restaurant` sets `table_id` on the order.

### 6.6 Interaction with pos_takeaway

The `pos_takeaway` module's `is_takeaway`/`is_dine_in` booleans will be **mapped** to `order_type`:
- `is_dine_in = True` → `order_type = 'mesa'`
- `is_takeaway = True` → `order_type = 'retira'` (default takeaway = pickup)

The new three-button selector **replaces** the TakeAway button in practice. The `pos_takeaway` module's button should be hidden (or its logic overridden) to avoid conflicts.

Options:
- **Option A**: Disable `pos_takeaway`'s button via config (`is_pos_takeaway = False`) and use our new buttons
- **Option B**: Override `pos_takeaway`'s JS to set `order_type` instead of `is_takeaway`/`is_dine_in`

**Recommendation**: Option A — simpler, no fork of Cybrosys code. Keep `pos_takeaway` installed for its receipt header logic but disable its POS button.

---

## Phase 7 — Data migration for existing tickets

### 7.1 Migration script

**File**: `addons/migrate_order_type.py` (run via odoo shell)

For all existing `pos.kitchen.ticket` records without `order_type`:
```python
tickets = env['pos.kitchen.ticket'].search([('order_type', '=', False)])
for t in tickets:
    if t.table_id:
        t.order_type = 'mesa'
    elif t.partner_id and t.partner_id.street:
        t.order_type = 'delivery'
    else:
        t.order_type = 'retira'
```

For all existing `pos.order` records without `order_type`:
```python
orders = env['pos.order'].search([('order_type', '=', False)])
for o in orders:
    if o.table_id:
        o.order_type = 'mesa'
    elif o.partner_id and o.partner_id.street:
        o.order_type = 'delivery'
    else:
        o.order_type = 'retira'
```

---

## Phase 8 — Testing

### 8.1 Unit tests

**File**: `custom_addons/pos_kitchen_screen_odoo/tests/test_kitchen_ticket.py`

Add tests:
1. `test_order_type_copied_to_ticket` — verify `get_or_create_ticket()` copies `order_type`
2. `test_order_type_in_get_details` — verify `get_details()` includes `order_type`
3. `test_delta_ticket_copies_order_type` — verify delta tickets get `order_type`
4. `test_order_type_default_mesa` — verify default is `mesa`

### 8.2 Printer tests

Update `custom_addons/pos_kitchen_receipt/sample.py`:
- Add sample tickets with explicit `order_type` values
- Verify output matches expected labels

### 8.3 Manual testing checklist

- [ ] Create mesa order → ticket shows MESA badge, printer shows MESA
- [ ] Create delivery order with partner → ticket shows DELIVERY, printer shows DELIVERY + address
- [ ] Create retira order → ticket shows RETIRO, printer shows RETIRA
- [ ] Create delivery with no address → printer shows "VER DIRECCION EN SISTEMA"
- [ ] Change order_type after ticket created → existing ticket unchanged, new delta gets new type
- [ ] KDS displays correct badge for all three types
- [ ] Pizza section headers correct on all three print types
- [ ] Legacy tickets (no order_type) still display correctly via fallback

---

## Execution Order

```
Phase 0  →  Fix v18 compatibility (prerequisite)
Phase 1  →  Add fields to pos.order (data model foundation)
Phase 2  →  Propagate to ticket (snapshot)
Phase 3  →  Update get_details() (API layer)
Phase 4  →  Update KDS frontend (display layer)
Phase 5  →  Update printer (output layer)
Phase 6  →  POS UI selector (input layer)
Phase 7  →  Data migration (existing records)
Phase 8  →  Testing (verification)
```

Phases 1-5 can be done in one session and tested immediately.
Phase 6.0 (PosOrder patch) MUST be done before 6.1-6.6 (buttons) — without it, order_type is silently lost during POS sync.
Phase 6.1-6.6 (POS UI buttons) is the most complex and may need iteration.
Phase 7 runs after deployment.

---

## Files Changed Summary

| File | Phase | Change |
|------|-------|--------|
| `pos_takeaway/static/src/js/.../ReceiptScreen.js` | 0 | Fix import path |
| `pos_takeaway/static/src/js/.../TakeAwayButton.js` | 0 | Fix buttonClass getter |
| `pos_takeaway/views/pos_order_view.xml` | 0 | Fix duplicate filter name |
| `pos_takeaway/__manifest__.py` | 0 | Version bump |
| `pos_kitchen_screen_odoo/models/pos_orders.py` | 1 | Add order_type + requested_time fields |
| `pos_kitchen_screen_odoo/views/pos_order_views.xml` | 1 | Add backend form fields |
| `pos_kitchen_screen_odoo/models/pos_kitchen_ticket.py` | 2,3 | Add order_type field, copy in create methods, add to get_details |
| `pos_kitchen_screen_odoo/static/src/js/kitchen_screen.js` | 4 | Replace getTicketType() |
| `pos_kitchen_screen_odoo/static/src/xml/kitchen_screen_templates.xml` | 4 | Replace heuristic conditionals |
| `pos_kitchen_receipt/models/ticket_printer.py` | 5 | Replace all heuristic logic |
| `pos_kitchen_screen_odoo/static/src/js/order_model.js` | 6 | New file — PosOrder patch (defaults) |
| `pos_kitchen_screen_odoo/static/src/js/order_type_buttons.js` | 6 | New file — POS selector |
| `pos_kitchen_screen_odoo/static/src/xml/order_type_buttons.xml` | 6 | New file — OWL template |
| `pos_kitchen_screen_odoo/__manifest__.py` | 6 | Register new assets |
| `addons/migrate_order_type.py` | 7 | New file — migration script |
| `pos_kitchen_screen_odoo/tests/test_kitchen_ticket.py` | 8 | Add new tests |
| `pos_kitchen_receipt/sample.py` | 8 | Update samples |

---

## Rules

1. **Ticket immutability**: Once created, `order_type` on a ticket never changes. Delta tickets inherit the current `order_type` from the order at creation time.
2. **POS enforcement**: The POS UI defaults to `mesa` when a table is selected. For delivery/retira, the cashier must explicitly select.
3. **No heuristics in production**: All downstream consumers (KDS, printer) read `order_type` directly. Fallback heuristic exists only for legacy data migration.
4. **pos_takeaway as UI-only**: The Cybrosys module stays installed for receipt headers but its POS button is disabled in favor of our three-state selector.
5. **Odoo 19 serialization is automatic**: `pos.order` fields are auto-loaded into the POS frontend schema and auto-serialized back. No `export_as_JSON` / `init_from_JSON` overrides needed (those methods don't exist in v19). Only `pos.order.line` requires explicit `_load_pos_data_fields` overrides.
