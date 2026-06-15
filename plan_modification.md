Now I have everything I need. Here's the final implementation plan:
Implementation Plan: KDS Philosophy Alignment
Goal
Align pos_kitchen_screen_odoo with the design philosophy from chat_gpt.md:
- 
POS is source of truth, KDS is a projection
- 
Line-level states are descriptive, not restrictive
- 
In-place updates for note changes (with MODIFICADO badge + manual acknowledge)
- 
Quantity changes still use delta tickets (addition/cancellation)
- 
Remove orphaned waiting state
- 
Ticket state becomes a derived summary, not a workflow gate
Change 1: models/pos_kitchen_ticket.py — Line model additions
Current (line 491-519):
class PosKitchenTicketLine(models.Model):
    _name = "pos.kitchen.ticket.line"
    ...
    note = fields.Char(string="Nota")
    state = fields.Selection([
        ("pending", "Pendiente"),
        ("cooking", "En Horno"),
        ("waiting", "Esperando Espacio"),  # ← orphaned
        ("ready", "Listo"),
        ("cancelled", "Cancelado"),
    ], default="pending", string="Estado")
Change to:
    note = fields.Char(string="Nota")
    note_snapshot = fields.Char(
        string="Nota al momento de envio",
        help="Snapshot of note when line was sent to kitchen. Used to detect note changes.")
    modified = fields.Boolean(
        string="Modificado",
        default=False,
        help="True when POS changed this line after it was sent to kitchen.")
    modified_at = fields.Datetime(string="Modificado a las")
    state = fields.Selection([
        ("pending", "Pendiente"),
        ("cooking", "En Horno"),
        ("ready", "Listo"),
        ("cancelled", "Cancelado"),
    ], default="pending", string="Estado")
Why:
- 
note_snapshot stores what the note was when the line was sent. Comparing it to the current POS note detects changes.
- 
modified + modified_at drive the MODIFICADO badge on the KDS.
- 
Remove waiting from the selection — it has no UI path and the philosophy only defines 4 states.
Change 2: models/pos_kitchen_ticket.py — Add acknowledge_modification() method
Add after action_toggle() (after line 585):
    def acknowledge_modification(self):
        self.ensure_one()
        self.modified = False
        self.modified_at = False
        self.env["bus.bus"]._sendone(
            f"pos_kitchen.{self.ticket_id.pos_config_id.id}", "notification", {
                "res_model": self._name,
                "message": "pos_order_line_acknowledged",
                "line_id": self.id,
                "ticket_id": self.ticket_id.id,
                "config_id": self.ticket_id.pos_config_id.id,
            })
Why: Kitchen staff taps the badge to confirm they've seen the change. Clears the flag and notifies all KDS clients.
Change 3: models/pos_kitchen_ticket.py — Loosen state transitions
Current (lines 29-44):
VALID_TRANSITIONS = {
    "pending": {"cooking", "cancelled"},
    "cooking": {"ready", "cancelled"},
    "waiting": {"cooking", "cancelled"},
    "ready": {"delivered", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}
LINE_TRANSITIONS = {
    "pending": {"cooking"},
    "cooking": {"ready", "cancelled"},
    "waiting": {"cooking", "cancelled"},
    "ready": {"cancelled"},
    "cancelled": set(),
}
Change to:
VALID_TRANSITIONS = {
    "pending": {"cooking", "cancelled"},
    "cooking": {"pending", "ready", "cancelled"},
    "ready": {"cooking", "delivered", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}
LINE_TRANSITIONS = {
    "pending": {"cooking", "cancelled"},
    "cooking": {"pending", "ready", "cancelled"},
    "ready": {"cooking", "cancelled"},
    "cancelled": {"pending"},
}
Why:
- 
Ticket: allow cooking → pending and ready → cooking so POS modifications can reset lines backward when needed.
- 
Lines: allow cancelled → pending so a cancelled line can be reactivated if POS re-adds it. Allow cooking → pending for the same reason.
- 
Remove all waiting entries.
- 
States are still tracked but no longer block POS-driven changes.
Change 4: models/pos_kitchen_ticket.py — Ticket state becomes derived summary
Current _sync_state_from_lines() (lines 131-149):
def _sync_state_from_lines(self):
    self.ensure_one()
    if not self.line_ids:
        return
    line_states = set(self.line_ids.mapped("state"))
    if line_states == {"ready"} or line_states == {"ready", "cancelled"}:
        if self.state != "ready":
            self.state = "ready"
            ...
    elif line_states == {"cancelled"}:
        ...
    elif "cooking" in line_states:
        if self.state == "pending":
            self.state = "cooking"
            ...
Change to:
def _sync_state_from_lines(self):
    self.ensure_one()
    if not self.line_ids:
        return
    line_states = set(self.line_ids.mapped("state"))
    if not line_states or line_states == {"cancelled"}:
        new_state = "cancelled"
    elif line_states == {"delivered"} or line_states == {"delivered", "cancelled"}:
        new_state = "delivered"
    elif line_states == {"ready"} or line_states == {"ready", "cancelled"}:
        new_state = "ready"
    elif "cooking" in line_states or "cooking" in line_states:
        new_state = "cooking"
    else:
        new_state = "pending"
    if self.state != new_state:
        self.state = new_state
        if new_state == "cooking":
            self.started_at = self.started_at or fields.Datetime.now()
            self._notify_kitchen("pos_order_accepted")
        elif new_state == "ready":
            self.ready_at = fields.Datetime.now()
            self._notify_kitchen("pos_order_completed")
        elif new_state == "cancelled":
            self._notify_kitchen("pos_order_cancelled")
Why: Ticket state is now purely derived from line states. No _transition() validation — it just reflects reality. This means the ticket state can move backward if lines move backward (e.g., POS modification resets a line from cooking to pending).
Change 5: models/pos_kitchen_ticket.py — Remove _transition() enforcement from progress_to_* methods
Current (lines 151-169):
def progress_to_cooking(self):
    self.ensure_one()
    self._transition("cooking")  # ← validates against VALID_TRANSITIONS
    ...
def progress_to_ready(self):
    self.ensure_one()
    self._transition("ready")
    ...
    self.line_ids.write({"state": "ready"})  # ← forces all lines to ready
    ...
Change to:
def progress_to_cooking(self):
    self.ensure_one()
    self.state = "cooking"
    self.started_at = fields.Datetime.now()
    pending_lines = self.line_ids.filtered(lambda l: l.state == "pending")
    pending_lines.write({"state": "cooking"})
    self._notify_kitchen("pos_order_accepted")
    return True
def progress_to_ready(self):
    self.ensure_one()
    self.state = "ready"
    self.ready_at = fields.Datetime.now()
    active_lines = self.line_ids.filtered(lambda l: l.state in ("pending", "cooking"))
    active_lines.write({"state": "ready"})
    self._notify_kitchen("pos_order_completed")
def progress_to_delivered(self):
    self.ensure_one()
    self.state = "delivered"
    self.delivered_at = fields.Datetime.now()
    self._notify_kitchen("pos_order_delivered")
Why:
- 
Remove _transition() calls — ticket state is now a derived summary, not a workflow gate.
- 
progress_to_cooking() only advances pending lines (not already-cooking or cancelled ones).
- 
progress_to_ready() only advances pending or cooking lines (not already-ready or cancelled).
- 
progress_to_delivered() doesn't touch line states — delivery is a ticket-level concept.
Change 6: models/pos_kitchen_ticket.py — Add modified field to get_details() serialization
Current get_details() line serialization (lines 272-288):
lines.append({
    "id": l.id,
    "product_id": l.product_id.id,
    "pos_order_line_id": l.pos_order_line_id.id,
    "full_product_name": l.full_product_name,
    "qty_total": l.qty_total,
    "qty_sent": l.qty_sent,
    "qty_ready": l.qty_ready,
    "qty_cancelled": l.qty_cancelled,
    "note": _extract_note_text(l.note),
    "state": l.state,
    "product_category": l.product_category or "",
    "category_label": CATEGORY_LABELS.get(cat, "OTROS"),
    "category_sort": CATEGORY_ORDER.index(cat) if cat in CATEGORY_ORDER else 99,
})
Add to the dict:
    "modified": l.modified,
    "modified_at": l.modified_at,
Why: KDS needs these fields to render the MODIFICADO badge.
Change 7: models/pos_kitchen_ticket.py — get_or_create_ticket() stores note_snapshot
Current (lines 354-368):
line_vals.append((0, 0, {
    "pos_order_line_id": order_line.id,
    "qty_total": qty,
    "qty_sent": qty,
    "note": _extract_note_text(order_line.note),
    "state": "pending",
    "product_category": product_category,
}))
Change to:
note_text = _extract_note_text(order_line.note)
line_vals.append((0, 0, {
    "pos_order_line_id": order_line.id,
    "qty_total": qty,
    "qty_sent": qty,
    "note": note_text,
    "note_snapshot": note_text,
    "state": "pending",
    "product_category": product_category,
}))
Why: note_snapshot captures what the note was at send time. Later, create_delta_tickets() compares current note to note_snapshot to detect changes.
Change 8: models/pos_kitchen_ticket.py — create_delta_tickets() detects note changes and updates in-place
Current (lines 388-473): Only checks delta = current_qty - sent_qty. If delta == 0, it continues — skipping the line entirely.
Change the if delta == 0: continue block to also check for note changes:
            current_qty = order_line.qty
            sent_qty = order_line.qty_sent_to_kitchen
            delta = current_qty - sent_qty
            current_note = _extract_note_text(order_line.note)
            # Find existing kitchen line for this pos_order_line
            existing_kitchen_line = self.env["pos.kitchen.ticket.line"].search([
                ("pos_order_line_id", "=", order_line.id),
                ("ticket_id.ticket_type", "=", "new"),
                ("state", "not in", ["cancelled"]),
            ], limit=1)
            # Detect note change
            note_changed = (
                existing_kitchen_line
                and existing_kitchen_line.note_snapshot != current_note
            )
            if delta == 0 and not note_changed:
                continue
            # Handle note change in-place
            if note_changed and existing_kitchen_line:
                existing_kitchen_line.write({
                    "note": current_note,
                    "note_snapshot": current_note,
                    "modified": True,
                    "modified_at": fields.Datetime.now(),
                })
                existing_kitchen_line.ticket_id._notify_kitchen("pos_order_line_modified")
            if delta == 0:
                continue
            # ... rest of existing delta logic unchanged ...
Why:
- 
When delta == 0 but the note changed, update the existing kitchen line in-place and set modified = True.
- 
The note_snapshot is updated to the new note so subsequent calls don't re-trigger.
- 
A new bus event pos_order_line_modified is sent so KDS can react.
- 
Quantity delta logic remains unchanged below.
Change 9: models/pos_kitchen_ticket.py — Add pos_order_line_modified to notification handler
Current onTicketNotification relevant events (in kitchen_screen.js line 383-388):
const relevant = [
    'pos_order_created', 'pos_order_updated', 'pos_order_paid',
    'pos_order_accepted', 'pos_order_cancelled', 'pos_order_completed',
    'pos_order_delivered', 'pos_order_line_updated',
    'pos_order_line_cooking', 'pos_order_line_ready', 'pos_order_line_cancelled',
];
Add 'pos_order_line_modified' and 'pos_order_line_acknowledged' to this list.
Change 10: models/pos_order_line.py — Add note_snapshot tracking field
Current (lines 1-15):
class PosOrderLine(models.Model):
    _inherit = "pos.order.line"
    qty_sent_to_kitchen = fields.Float(...)
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list.append("qty_sent_to_kitchen")
        return fields_list
Change to:
class PosOrderLine(models.Model):
    _inherit = "pos.order.line"
    qty_sent_to_kitchen = fields.Float(
        default=0.0,
        help="Cantidad ya enviada a cocina. Se usa para detectar adiciones o cancelaciones."
    )
    note_sent_to_kitchen = fields.Char(
        default="",
        help="Snapshot of note when last sent to kitchen. Used to detect note changes."
    )
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list.append("qty_sent_to_kitchen")
        fields_list.append("note_sent_to_kitchen")
        return fields_list
Why: Store the note snapshot on the POS order line itself (not just the kitchen ticket line) so create_delta_tickets() can compare without joining across models. This is the "last sent" state from the POS perspective.
Change 11: static/src/js/kitchen_screen.js — Add acknowledge action and MODIFICADO rendering
Add method after cancelLine() (after line 556):
    async acknowledgeModification(ev, line) {
        ev.stopPropagation();
        try {
            await this.orm.call("pos.kitchen.ticket.line", "acknowledge_modification", [line.id]);
        } catch (error) {
            console.error("Error acknowledging modification:", error);
        }
    }
Add 'pos_order_line_modified' and 'pos_order_line_acknowledged' to the relevant array in onTicketNotification() (line 383).
Change 12: static/src/xml/kitchen_screen_templates.xml — Add MODIFICADO badge and acknowledge button
After the line status badge (after line 183), add:
<t t-if="line.modified">
    <span class="kds-line-status kds-line-status--modified">MODIFICADO</span>
    <button class="kds-line-btn-ack"
            t-on-click.stop="(e) => this.acknowledgeModification(e, line)">
        OK
    </button>
</t>
Change 13: static/src/css/kitchen_screen.css — Add MODIFICADO badge styles
Add after .kds-line-status--cancelled (after line 615):
.kds-line-status--modified {
    background-color: #f59e0b;
    color: #000;
    animation: kdsPulse 2s infinite;
}
.kds-line-btn-ack {
    background: none;
    border: 1px solid #f59e0b;
    color: #f59e0b;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
    transition: background-color 0.15s;
    min-width: 28px;
    min-height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.kds-line-btn-ack:hover {
    background-color: #f59e0b;
    color: #000;
}
Change 14: static/src/js/kitchen_screen.js — Remove waiting state from UI
Current state tabs (lines 44-47):
this.pendingStage = () => { this.state.stages = 'pending'; };
this.cookingStage = () => { this.state.stages = 'cooking'; };
this.readyStage = () => { this.state.stages = 'ready'; };
this.deliveredStage = () => { this.state.stages = 'delivered'; };
No change needed here — waiting is already not a tab. But in _recomputeDerived() (line 311), the counts don't include waiting. No change needed.
In kitchen_screen_templates.xml: The template already doesn't render a waiting tab. No change needed.
In getLineStatusLabel() (line 169-178): Remove the waiting entry:
getLineStatusLabel(state) {
    const labels = {
        pending: _t('Pend'),
        cooking: _t('Horno'),
        ready: _t('Listo'),
        cancelled: _t('X'),
    };
    return labels[state] || state;
}
Change 15: tests/test_kitchen_ticket.py — Update tests
Tests that need updating:
1. 
test_line_state_cycle (line 127): Remove waiting references. Update cycle to match new LINE_TRANSITIONS.
2. 
test_ticket_state_advance (line 156): Should still pass — pending → cooking → ready → delivered is still valid.
3. 
Add new test test_note_change_in_place: Create order with note, create ticket, change note on pos.order.line, call create_delta_tickets(), assert existing kitchen line's note updated and modified = True, no new ticket created.
4. 
Add new test test_acknowledge_modification: Set modified = True, call acknowledge_modification(), assert modified = False.
5. 
Add new test test_backward_state_transition: Move line to cooking, then back to pending. Assert it works without ValidationError.
Change 16: models/pos_session.py — Delete file
Current: Stub with only comments. No active code.
Action: Delete the file and remove from . import pos_session from models/__init__.py (line 26).
Change 17: static/src/js/order_pay.js — Delete file
Current: No-op passthrough patch on _finalizeValidation().
Action: Delete the file and remove it from __manifest__.py point_of_sale.assets_prod list (line 65).
Implementation Order
1. 
Backend model changes (Changes 1-8, 10) — pos_kitchen_ticket.py + pos_order_line.py
2. 
Backend cleanup (Changes 16-17) — Delete dead files
3. 
Frontend JS (Changes 9, 11, 14) — kitchen_screen.js
4. 
Frontend template (Change 12) — kitchen_screen_templates.xml
5. 
Frontend CSS (Change 13) — kitchen_screen.css
6. 
Tests (Change 15) — test_kitchen_ticket.py
7. 
Run tests to verify
What This Plan Does NOT Change
- 
Delta tickets for quantity changes — Still work exactly as before (addition/cancellation tickets with batch letters)
- 
Bus channel architecture — Still pos_kitchen.{config_id} (the channel name mismatch is a separate bug, not part of this philosophy alignment)
- 
Payment flow — Still updates payment_status on tickets
- 
Order type buttons — Mesa/Delivery/Retira unchanged
- 
Oven queue indicator — Still computed from cooking-state lines
- 
Station filtering — Still works by product category
- 
Undo toast — Still 5-second window
- 
Auto-refresh — Still 30-second polling fallback
- 
kitchen.screen config model — Unchanged
- 
product.product.prepair_time_minutes — Unchanged
Risk Assessment
Risk	Mitigation
Removing waiting state breaks existing data	Migration: any existing waiting lines get moved to pending
Loosening VALID_TRANSITIONS allows invalid UI states	Frontend still only shows forward transitions; backward is only triggered by POS sync
note_snapshot comparison fails on JSON formatting differences	_extract_note_text() normalizes to plain text before comparison
modified badge appears on lines that were already delivered	acknowledge_modification() can be called from any state; also, delivered lines are filtered from active view