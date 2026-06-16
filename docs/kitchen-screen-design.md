# POS Kitchen Screen — Design Specification

## Philosophy

The KDS is **not a ticket workflow system**. It is a **stage projection system**.

A ticket may appear in multiple tabs because tabs represent:

> "What work exists at this stage right now?"

not

> "What is the overall state of this order?"

The source of truth remains the ticket lines in the database. The frontend renders stage-specific projections of those lines. This pattern is called **Contextual Multi-Stage Projection**.

```
Kitchen Ticket
        ↓
Kitchen Lines (source of truth)
        ↓
Stage Projections
        ↓
Contextual Cards
        ↓
Advance Visible Items
```

A card appearing in multiple tabs is not a bug — it is a deliberate projection. The cook sees the full order context in every tab, with only the lines belonging to the current stage being actionable.

---

## Layout Structure

```
┌────────────────────────────────────────────────────────────────────┐
│  PREP HEADER (collapsible)                                         │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Resumen de Preparacion                    [Expandir/Ocultar]  │ │
│  │  3x Margarita  2x Fugazzeta  1x Empanada Carne (URGENTE)     │ │
│  └──────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────┤
│  STATION TABS:  [Todas] [Pizza] [Empanada] [Bebida] [Otro]        │
├────────────────────────────────────────────────────────────────────┤
│  OVEN QUEUE:  ● 4/6  — Espacio en horno: 4/6 — 0 esperando        │
├────────────────────────────────────────────────────────────────────┤
│  STATE TABS:  [Pendiente 3] [En Horno 2] [Listo 1] [Entregado 0]  │
├────────────────────────────────────────────────────────────────────┤
│  TICKET GRID (4-column responsive)                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  │ Card #1      │ │ Card #2      │ │ Card #3      │ │ Card #4      │
│  │ ─────────    │ │ ─────────    │ │ ─────────    │ │              │
│  │ Header       │ │ Header       │ │ Header       │ │              │
│  │ · ID/Client  │ │ · ID/Client  │ │ · ID/Client  │ │              │
│  │ · Time badge │ │ · Time badge │ │ · Time badge │ │              │
│  │ · Type badge │ │ · Type badge │ │ · Type badge │ │              │
│  │ ─────────    │ │ ─────────    │ │ ─────────    │ │              │
│  │ PIZZAS       │ │ PIZZAS       │ │ EMPANADAS    │ │              │
│  │  1x Marga─   │ │  2x Napol─   │ │  1x Carne     │ │              │
│  │    (active)  │ │    (active)  │ │   (active)    │ │              │
│  │ ~~2x Fugaz~~ │ │              │ │               │ │              │
│  │ ─────────    │ │ ─────────    │ │ ─────────    │ │              │
│  │ → MOVER 1    │ │ → MOVER 2    │ │ → MOVER 1    │ │              │
│  │ ─────────    │ │ ─────────    │ │ ─────────    │ │              │
│  │ ←Anterior    │ │ ←Anterior    │ │ ←Anterior     │ │              │
│  │ Imprimir     │ │ Imprimir     │ │ Imprimir      │ │              │
│  │ Cancelar     │ │ Cancelar     │ │               │ │              │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
├────────────────────────────────────────────────────────────────────┤
│  UNDO TOAST (bottom center, slides up, 5s)                        │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Ticket movido a En Horno                    [DESHACER]       │ │
│  │ ████████████░░░░░░░░  (progress bar)                        │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### Card Anatomy

```
┌─────────────────────────────────┐
│ ! (sync error, if failed)       │
│ ┌─────────────────────────────┐ │
│ │ #3201B • MESA 4  ·  12 MIN │ │  Header Row 1: ID+Batch • Client/Table • SLA timer
│ │ NUEVO  │  MESA  │ FALTA PAGAR│ │  Header Row 2: TicketType • OrderType • Payment
│ └─────────────────────────────┘ │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│ PIZZAS                          │  Category section header
│  2x Margarita      Pend      X │  Active line: qty • name • status badge • cancel
│  1x Fugazzeta      Listo  ← X │  Line with prev+cancel buttons
│  ┌─ Nota: Sin cebolla ──────┐ │  Note block (red = sin, green = extra)
│  └──────────────────────────┘ │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│ → MOVER 2 ITEMS A HORNO        │  Action label with affected count
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│ ← Anterior  Imprimir  Cancelar │  Footer buttons
└─────────────────────────────────┘
```

---

## Projection Rules

A ticket can be rendered in several tabs simultaneously because each tab is a stage-specific projection of the ticket's lines.

Given a ticket with mixed line states:

```
Ticket #3201
────────────────
Empanada      pending
Margarita     cooking
Fugazzeta     ready
```

### Pendiente

```
#3201 • Mesa 4

1x Empanada                   ← active
~~2x Margarita~~              ← already cooking
~~1x Fugazzeta~~              ← already ready

→ MOVER 1 ITEM A HORNO
```

### En Horno

```
#3201 • Mesa 4

~~1x Empanada~~               ← still pending
2x Margarita                   ← active
~~1x Fugazzeta~~              ← already ready

→ MOVER 1 ITEM A LISTO
```

### Listo

```
#3201 • Mesa 4

~~1x Empanada~~               ← still pending
~~2x Margarita~~              ← still cooking
1x Fugazzeta                   ← active

→ ENTREGAR 1 ITEM
```

### Projection Data Structure

```python
class TicketProjection:
    ticketId: int
    stage: str                       # 'pending' | 'cooking' | 'ready' | 'delivered'
    active_lines: list[Line]         # lines where line.state == stage
    context_lines: list[ContextLine] # lines where line.state != stage
    affected_count: int              # how many lines will be advanced
    has_previous_items: bool         # any lines in a stage before this one
    has_future_items: bool           # any lines in a stage after this one
    requires_confirmation: bool      # has_previous_items is True
    can_advance: bool                # active_lines is non-empty
```

The frontend becomes declarative:

```javascript
if (projection.requiresConfirmation) {
    showConfirm();
}
```

No complex state reasoning in JS.

---

## Visual Rules

For the current stage tab:

| Line relationship | Visual treatment     | CSS class           |
|-------------------|---------------------|---------------------|
| active            | normal              | `kds-line`          |
| previous          | strike-through      | `kds-line--prev`    |
| future            | dimmed (50% opacity)| `kds-line--future`  |
| cancelled         | faded (30% opacity) | `kds-line--cancelled` |
| modified          | highlighted + pulse | `kds-line--modified`|

Example in the Cooking tab:

```
~~1x Empanada~~              ← still pending (previous)
2x Margarita                  ← active
··1x Fugazzeta               ← already ready (future)
✕ 1x Bebida                   ← cancelled
⚠ 1x Napolitana MODIFICADO   ← note modified
```

### Relationship Definitions

```python
STAGE_ORDER = ["pending", "cooking", "ready"]

def line_relationship(line_state: str, tab_stage: str) -> str:
    if line_state == tab_stage:
        return "active"
    if line_state == "cancelled":
        return "cancelled"
    idx_line = STAGE_ORDER.index(line_state) if line_state in STAGE_ORDER else -1
    idx_tab = STAGE_ORDER.index(tab_stage)
    if idx_line < idx_tab:
        return "previous"
    return "future"
```

This preserves kitchen context while making the actionable items obvious.

---

## Card Actions

Card actions no longer mean **"Advance ticket"**. They mean **"Advance visible items"**.

### Action Labels (dynamic)

```
→ MOVER 3 ITEMS A HORNO      # pending → cooking
→ MOVER 2 ITEMS A LISTO       # cooking → ready
→ ENTREGAR 1 ITEM            # ready → delivered
```

The number and destination are always visible. The cook understands exactly what will happen.

### Behavior

When the cook taps the card body:

1. Only lines matching the current tab's stage are advanced.
2. Lines in other stages are NOT touched.
3. The card may remain in the current tab if other lines still match the stage.
4. If no lines remain in the stage, the card exits the tab (with `CARD_TRANSITION_MS` fade).

---

## Confirmation Rules

If the projection contains items in a **previous** stage, show a confirmation dialog.

### Example

The cook is in the **En Horno** tab. A ticket has:

```
Pendiente:
  1 Empanada              ← previous-stage line

En Horno:
  2 Margaritas            ← active lines
```

Cook taps `→ MOVER 2 ITEMS A LISTO`.

Show:

```
╔══════════════════════════════════════════╗
║  ⚠️  Todavía hay productos en Pendiente  ║
║                                          ║
║  Pendiente:                              ║
║    • 1 Empanada                          ║
║                                          ║
║  ¿Mover únicamente los 2 productos       ║
║  en horno a Listo?                       ║
║                                          ║
║       [Cancelar]    [Continuar]          ║
╚══════════════════════════════════════════╝
```

### What is NOT blocked

The action is **never blocked**. In a real kitchen, items move independently — a pizza may be ready while an empanada is still being assembled. The confirmation provides safety without imposing an unrealistic workflow.

### When Confirmation Triggers

```python
projection.requires_confirmation = projection.has_previous_items
```

Only previous-stage items trigger confirmation (forward-tab items do not — those are naturally later in the workflow).

---

## State Model

### Current (problematic)

```javascript
ticket.state  // derived from lines, ambiguous meaning
```

### Proposed

```javascript
projection = {
    ticketId,
    stage,               // the tab this projection is for
    activeLines,         // lines actionable in this tab
    contextLines,        // all other lines (previous, future, cancelled)
    affectedCount,       // how many items will move
    hasPreviousItems,    // any items in earlier stages
    requiresConfirmation,// derived: hasPreviousItems
}
```

The ticket itself has **no UI state**. The projection has UI state.

---

## Backend Architecture

```
POS Order
    ↓
Kitchen Ticket
    ↓
Kitchen Ticket Lines (source of truth)
    ↓
Projection Builder (server-side)
    ↓
KDS (renders projections)
```

### Module Dependencies

```
pos_kitchen_screen_odoo (KDS display + ticket state)
         ↑ depends_on
pos_kitchen_receipt (thermal printing)
         │   provides: kitchen.ticket.printer
         │   provides: _get_product_category()
         │   provides: ESC/POS formatting + CUPS lp
```

`pos_kitchen_receipt` supplies the `kitchen.ticket.printer` AbstractModel that the KDS module calls for printing (`print_ticket`) and category lookup (`_get_product_category`). Every card can print at any time via the "Imprimir" button — no additional wiring needed.

Bus notifications are **invalidation signals only** — not state updates:

```
Database
    ↓
Commit
    ↓
Bus invalidate
    ↓
Projection reload (from server)
```

The frontend should never become the source of truth. Every mutation is confirmed by the server before the UI settles.

### Server-Side Projection Endpoint

```python
@api.model
def get_projections(self, shop_id, stage, version=0):
    """Return all projections for a given stage, with version check."""
    tickets = self.search([
        ("pos_config_id", "=", shop_id),
        ("state", "not in", ["delivered", "cancelled"]),
    ])
    projections = []
    for ticket in tickets:
        proj = self._build_projection(ticket, stage)
        if proj and proj.active_lines:
            projections.append(proj)
    return {
        "projections": projections,
        "version": self._current_version(shop_id),
        "oven_capacity": self._get_oven_capacity(shop_id),
        "oven_available": self._get_oven_available(shop_id),
    }
```

---

## Frontend Store

### Current (problematic)

```javascript
useState({
    tickets,            // domain objects mutated in-place
    ghosting,           // transient UI bolted onto domain
    transitioning,      // transient UI bolted onto domain
    syncError,          // transient UI bolted onto domain
    undoToast,          // mixed with domain state
})
```

### Proposed

```javascript
state = {
    entities: {
        tickets: Map(),    // domain objects, never mutated by UI
        lines: Map(),
    },

    projections: {
        byStage: {
            pending: [],
            cooking: [],
            ready: [],
            delivered: [],
        },
        counts,            // per-tab badge counts
        prepSummary,       // consolidated prep counts
        ovenQueue,         // { available, capacity, waiting }
    },

    ui: {
        activeStage: 'pending',
        activeStation: 'all',
        toast: null,          // { message, undoCommand, expiresAt }
        ghosting: Set(),
        transitioning: Set(),
        syncErrors: Map(),    // ticketId → error message
        confirmation: null,   // { ticketId, previousItems, action }
    }
}
```

Transient UI state never mutates domain objects. Projections are recomputed from entities when any entity changes.

---

## Versioning

Eliminate all race conditions with a projection version counter.

### Server

```python
class KitchenScreen(models.Model):
    # ... existing fields ...
    projection_version = fields.Integer(default=0)

    def _bump_version(self):
        self.projection_version += 1
```

Every mutation calls `_bump_version()`. The version is included in every API response and bus notification.

### Frontend

```javascript
onTicketNotification(message) {
    if (message.version <= this.state.version) {
        return; // stale notification, discard
    }
    this.state.version = message.version;
    this.loadProjections();
}
```

This solves:
- Poll vs bus races
- Duplicate notifications
- Multi-screen edits
- Visibility reload races
- Flickering from stale data

---

## State Machine

Move all transition logic server-side into a dedicated class.

### Current (problematic)

```python
LINE_TRANSITIONS = {
    "pending": {"cooking", "cancelled"},
    "cooking": {"pending", "ready", "cancelled"},
    # ...
}
```

Scattered validation in `action_cooking()`, `action_ready()`, etc.

### Proposed

```python
class KitchenStateMachine:
    """Encapsulates all kitchen line transition logic."""

    STAGE_ORDER = ["pending", "cooking", "ready", "delivered"]
    VALID_TRANSITIONS = {
        "pending":   {"cooking", "cancelled"},
        "cooking":   {"pending", "ready", "cancelled"},
        "ready":     {"cooking", "cancelled"},
        "cancelled": {"pending"},
    }

    @classmethod
    def next(cls, line):
        if line.state not in cls.VALID_TRANSITIONS:
            raise InvalidTransition(f"Unknown state: {line.state}")
        allowed = cls.VALID_TRANSITIONS[line.state]
        if "cooking" in allowed:
            return line._transition("cooking")
        if "ready" in allowed:
            return line._transition("ready")
        raise InvalidTransition(f"No forward transition from {line.state}")

    @classmethod
    def previous(cls, line):
        idx = cls.STAGE_ORDER.index(line.state) if line.state in cls.STAGE_ORDER else -1
        if idx > 0:
            return line._transition(cls.STAGE_ORDER[idx - 1])
        return line.state

    @classmethod
    def can_transition(cls, src, dst):
        return dst in cls.VALID_TRANSITIONS.get(src, set())

    @classmethod
    def advance_visible(cls, ticket, stage):
        """Advance only lines matching the given stage."""
        affected = ticket.line_ids.filtered(lambda l: l.state == stage)
        snapshots = [{"line_id": l.id, "state": l.state} for l in affected]
        if stage == "pending":
            affected.write({"state": "cooking"})
        elif stage == "cooking":
            affected.write({"state": "ready"})
        elif stage == "ready":
            ticket.state = "delivered"
            ticket.delivered_at = fields.Datetime.now()
        ticket._sync_state_from_lines()
        return snapshots
```

The frontend only calls `advance_visible()` — the server decides what is allowed.

---

## Undo

### Current (problematic)

```
optimistic update → RPC → maybe fail → undo → maybe fail
```

- Cancel undo restores everything to `pending` (line states lost)
- No snapshot of previous state
- Undo calls reverse method regardless of forward success

### Proposed

Store snapshots on every mutation:

```python
class KitchenActionLog(models.Model):
    _name = "kitchen.action.log"
    _description = "Kitchen Action Log (for undo)"

    ticket_id = fields.Many2one("pos.kitchen.ticket", required=True, ondelete="cascade")
    action = fields.Char(required=True)  # 'advance_visible', 'cancel_ticket', etc.
    stage = fields.Char()                # stage the action was taken from
    previous_line_states = fields.Json() # [{line_id: 12, state: "cooking"}, ...]
    created_at = fields.Datetime(default=fields.Datetime.now)
```

Undo restores exact states:

```python
def undo_last_action(self):
    log = self.env["kitchen.action.log"].search([
        ("ticket_id", "=", self.id),
    ], order="created_at desc", limit=1)
    if not log:
        return False
    for entry in log.previous_line_states:
        line = self.env["pos.kitchen.ticket.line"].browse(entry["line_id"])
        line.state = entry["state"]
    self._sync_state_from_lines()
    log.unlink()
    return True
```

### Cleanup

Actions older than `UNDO_WINDOW_MS` are purged periodically:

```python
@api.autovacuum
def _gc_action_log(self):
    threshold = fields.Datetime.now() - timedelta(seconds=UNDO_WINDOW_MS + 60)
    self.search([("created_at", "<", threshold)]).unlink()
```

---

## Bug Fixes

### Printer: Resolved by `pos_kitchen_receipt`

The `kitchen.ticket.printer` model is provided by the companion module `pos_kitchen_receipt` (`custom_addons/pos_kitchen_receipt/models/ticket_printer.py`), which depends on `pos_kitchen_screen_odoo`. It handles:

- ESC/POS formatting via `format_ticket_escpos()` — full thermal receipt layout with categories, notes, address, total
- CUPS printing via `subprocess.run(["lp", "-d", printer, "-o", "raw"], ...)`
- Printer name from `kitchen.screen.printer_name`
- Logo embedding from `_logo.py`
- `_get_product_category()` — also delegated to by `pos_kitchen_ticket._get_product_category()` at `pos_kitchen_ticket.py:254`

No bug here. Printing works from any card at any time via the "Imprimir" button.

### P1: Note + Qty Simultaneous Change Silently Drops Delta

**Current:** `get_details()` deduplicates by `pos_order_line_id`. When a note change updates the base line in-place AND a qty delta creates a new ticket line, the delta line is skipped because `pid in seen_pol_ids` returns `True`.

**Fix:** Give every kitchen ticket line its own identity:

```python
class PosKitchenTicketLine(models.Model):
    origin_pos_order_line_id = fields.Many2one("pos.order.line")  # unchanged FK
    kitchen_line_id = fields.Integer()  # unique per creation event
```

In `get_details()`, deduplicate by `kitchen_line_id` instead of `pos_order_line_id`. The note-change-in-place updates the original line's note without creating a new `kitchen_line_id`. The delta ticket creates a new `kitchen_line_id`. Both survive the merge.

### P1: Cancel Undo Resets All Line States

**Current:** `kitchen_screen.js:611-621` — undo comment: "We don't have per-line previous state stored, so just reload".

**Fix:** Use the `KitchenActionLog` snapshot system described in the Undo section above. Undo restores exact per-line states from the JSON snapshot.

### P1: Oven Capacity Hardcoded in JS

**Current:** `kitchen_screen.js:9` — `const OVEN_CAPACITY = 6`. Never synced from server.

**Fix:**
1. Remove the JS constant.
2. Include `oven_capacity` and `oven_available` in the `get_projections()` response.
3. Frontend uses server values exclusively.

### P2: Bus Channel Name Drift

**Current:** Channel name constructed independently in Python (`pos_kitchen_sync.py:14`) and JavaScript (`kitchen_screen.js:65`). If either changes without the other, real-time push silently breaks.

**Fix:** Define once:

```python
# pos_kitchen_sync.py
KITCHEN_BUS_CHANNEL_PREFIX = "pos_kitchen"

@classmethod
def channel_for(cls, config_id):
    return f"{cls.KITCHEN_BUS_CHANNEL_PREFIX}.{config_id}"
```

```javascript
// kitchen_screen.js
this.channel = `pos_kitchen.${this.currentShopId}`;
// Comment references the Python prefix constant by name
```

Use a shared test that asserts both sides produce the same channel string for the same config ID.

---

## Error Scenarios (Current Implementation)

### 1. Mixed-State Card After Partial Advancement

Cook advances individual lines to different states. Card appears in multiple tabs simultaneously. Clicking the card in one tab only advances lines matching that tab's stage — other lines are left behind.

**Design response:** The projection system makes this explicit. The action label shows the count (`→ MOVER 1 ITEM A HORNO`), context lines are shown as strike-through, and the confirmation dialog warns about skipped items.

### 2. Optimistic Update Failure During Undo Window

Card optimistically moves to next stage. ORM call fails. Undo calls `revert_to_previous()` on a ticket that never changed server-side.

**Design response:** Versioned projections prevent stale-state undo. The action log stores the pre-mutation snapshot. Undo restores from snapshot regardless of whether the forward mutation succeeded server-side.

### 3. Cancel-Undo Race Condition

`_pendingCancels` Set prevents duplicate reloads during cancel, but brief flicker possible when set is cleared before final load completes.

**Design response:** Version counter eliminates the race entirely. Incoming updates with `version <= current.version` are discarded. The `_pendingCancels` guard becomes unnecessary.

### 4. Note Modification Without Delta Ticket

Note change updates base line in-place. Simultaneous qty change creates delta ticket line. `seen_pol_ids` dedup drops the delta.

**Design response:** `kitchen_line_id` replaces `pos_order_line_id` as the dedup key. In-place modifications and new delta lines get separate identities.

### 5. Ghost/Delivery Card Inconsistent Across Tabs

One screen shows graceful 10s fade, another shows abrupt disappearance because `_reloadOrderTickets()` replaces the card without ghosting.

**Design response:** Ghosting is moved to the `ui` substore, keyed by `ticketId`. When a bus notification arrives with a delivered ticket, the UI layer checks `ui.ghosting` before removing the card. Ghosting persists across reloads until the `GHOST_DURATION_MS` expires.

---

## Implementation Priorities

| Priority | Item | Effort | Risk Reduction |
|----------|------|--------|----------------|
| P1 | Note+qty dedup fix (`kitchen_line_id`) | 4h | Prevents silent data loss |
| P1 | Cancel undo with snapshots | 4h | Prevents lost line state |
| P1 | Oven capacity from server | 2h | Prevents stale config |
| P1 | Confirmation dialog for skipped items | 3h | Prevents cook errors |
| P2 | Projection builder (server-side) | 8h | Foundation for all visual fixes |
| P2 | Frontend store separation (entities/ui) | 6h | Prevents state corruption |
| P2 | Version counter for projections | 3h | Eliminates all race conditions |
| P2 | Bus channel constant sharing | 1h | Prevents silent push failure |
| P3 | Contextual line rendering (strike-through/dim) | 4h | Improves cook UX |
| P3 | Dynamic action labels with counts | 2h | Improves cook confidence |
| P3 | KitchenStateMachine class | 3h | Cleaner transition logic |

---

## Migration Path

The design allows incremental adoption:

1. **Phase 1 (backend only):** Add `projection_version`, `KitchenActionLog`, `kitchen_line_id`. No frontend changes. Existing KDS works unchanged.
2. **Phase 2 (server projection):** Add `get_projections()` endpoint with projection builder. Run alongside `get_details()`.
3. **Phase 3 (frontend store):** Refactor JS store to separated entities/ui. Consume new projection endpoint.
4. **Phase 4 (visual rules):** Implement contextual line rendering, dynamic action labels, confirmation dialog.
5. **Phase 5 (remove legacy):** Remove `get_details()`, old `LINE_TRANSITIONS` scattered checks, `_pendingCancels`.

Each phase is independently deployable and reversible.
