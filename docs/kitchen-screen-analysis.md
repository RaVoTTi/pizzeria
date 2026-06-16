# POS Kitchen Screen — UI/UX Workflow, State Architecture & Risk Analysis

## 1. Layout Structure

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
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ amber ─ ─ red ─ ─green─ ─ blue ─ ─ ─ ─ ─ ─ │
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
│  │    (Pend)    │ │    (Horno)   │ │   (Listo)     │ │              │
│  │ ─────────    │ │ ─────────    │ │ ─────────    │ │              │
│  │ TAP→ AL HORNO│ │ TAP→ LISTO   │ │ TAP→ ENTREGADO│ │              │
│  │ ─────────    │ │ ─────────    │ │ ─────────    │ │              │
│  │ ←Anterior    │ │ ←Anterior    │ │ ←Anterior     │ │              │
│  │ Imprimir     │ │ Imprimir     │ │ Imprimir      │ │              │
│  │ Cancelar     │ │ Cancelar     │ │               │ │              │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
├────────────────────────────────────────────────────────────────────┤
│  UNDO TOAST (bottom center, slides up)                            │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Ticket movido a En Horno                    [DESHACER]       │ │
│  │ ████████████░░░░░░░░  (progress bar, 5s)                    │ │
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
│  2x Margarita      Pend      X │  Line: qty • name • status • cancel
│  1x Fugazzeta      Listo  ← X │  Line with prev+cancel buttons
│  ┌─ Nota: Sin cebolla ──────┐ │  Note block (red = sin, green = extra)
│  └──────────────────────────┘ │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│ TAP — AL HORNO                 │  Next-action hint
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│ ← Anterior  Imprimir  Cancelar │  Footer buttons
└─────────────────────────────────┘
```

---

## 2. State Machine

### 2.1 Card (Ticket) State Transitions

```
                    ┌──────────┐
                    │ PENDING  │  Card created from POS order
                    └────┬─────┘
                         │ progress_to_cooking()  ← click card
                         ▼
                    ┌──────────┐
              ┌─────│ COOKING  │─────┐
              │     └────┬─────┘     │
              │ revert_  │  progress_│ to_ready()  ← click card
              │ previous │           │
              │          ▼           │
              │     ┌──────────┐     │
              │     │  READY   │◄────┘
              │     └────┬─────┘
              │          │ progress_to_delivered()  ← click card
              │          ▼
              │     ┌───────────┐
              │     │ DELIVERED │─── 10s ghost → removed from grid
              │     └───────────┘
              │
              │  cancel_ticket()  ← Cancelar Ticket button (from any state)
              ▼
         ┌──────────┐
    ┌────│CANCELLED │  Hidden from grid immediately
    │    └──────────┘
    │ undo (5s window)
    └──────────────→ restored to previous state
```

### 2.2 Line (Per-Product) State Transitions

```
         ┌──────────┐
    ┌───→│ PENDING  │
    │    └────┬─────┘
    │         │ action_cooking() / click line
    │         ▼
    │    ┌──────────┐
    │    │ COOKING  │
    │    └────┬─────┘
    │         │ action_ready() / click line
    │         ▼
    │    ┌──────────┐
    │    │  READY   │
    │    └────┬─────┘
    │         │ action_cancel() / click line
    │         ▼
    │    ┌──────────┐
    │    │CANCELLED │
    │    └────┬─────┘
    │         │ click line (action_toggle)
    └─────────┘
```

**Backward transitions** (via `onLinePrevious` / `action_previous`):

| From | To |
|------|----|
| cooking | pending |
| ready | cooking |
| cancelled | ready |

**Validation**: Server-side `LINE_TRANSITIONS` dict guards against invalid jumps:
```python
LINE_TRANSITIONS = {
    "pending":   {"cooking", "cancelled"},
    "cooking":   {"pending", "ready", "cancelled"},
    "ready":     {"cooking", "cancelled"},
    "cancelled": {"pending"},
}
```

### 2.3 Ticket State Derivation (from Lines)

The card's overall state is derived from its lines (`_deriveTicketState()` in JS, `_sync_state_from_lines()` in Python):

| Line States Present | Ticket State |
|--------------------|--------------|
| Any line pending | pending |
| Any line cooking (no pending) | cooking |
| Any line ready (no pending/cooking) | ready |
| Only cancelled | cancelled |
| Empty | pending |

This means a card can appear in multiple tabs simultaneously. A ticket with line A cooking and line B pending will appear in both "Pendiente" and "En Horno" tabs.

---

## 3. Checklist System

### 3.1 Per-Line Progress Tracking

Each product line on a ticket is independently tracked as a checklist item. The cook taps a line to advance it through stages. This allows a pizza with 3 products (2x Margarita + 1x Fugazzeta) to have each line at a different stage.

### 3.2 Visual Line States

| State | CSS Class | Appearance |
|-------|-----------|-----------|
| pending | `kds-line` (default) | Full opacity, normal weight |
| cooking | `kds-line` (default) | Full opacity, normal weight |
| ready | `kds-line--ready` | Strikethrough text |
| cancelled | `kds-line--cancelled` | Dimmed, faded |
| In other tab | `kds-line--dimmed` | Reduced opacity (50%) |
| New/addition | `kds-line--new` | Left border highlight + brightness |

### 3.3 Line Interaction Buttons

| Button | Visibility | Action |
|--------|-----------|--------|
| `←` (Previous) | Line not pending and not cancelled | Reverts to previous state |
| `X` (Cancel) | Line not cancelled | Cancels the line |
| `OK` (Acknowledge) | Line has `modified=true` | Confirms note change seen |

### 3.4 Card Interaction Buttons

| Button | Visibility | Action |
|--------|-----------|--------|
| Card body click | Always (if not delivered/cancelled) | Advances all pending→cooking or cooking→ready or ready→delivered |
| `← Anterior` | Not pending, not cancelled | Reverts card to previous state |
| `Imprimir` | Always | Sends to CUPS printer |
| `Cancelar Ticket` | Not cancelled | Cancels entire order |

---

## 4. Five Error-Prone Card Situations

### 4.1 Mixed-State Card After Partial Advancement

**Scenario:** A ticket has 3 lines: Margarita (pending), Fugazzeta (pending), Empanada (pending). The cook taps individual lines to advance them to different states. Margarita → cooking, Empanada → cancelled, Fugazzeta still pending.

**What happens:**
- The ticket appears in BOTH "Pendiente" tab AND "En Horno" tab simultaneously
- Clicking the card in "Pendiente" tab calls `_advanceTicket()` → `progress_to_cooking()` — but this code only advances lines whose `state === this.state.stages` (the current tab). Only Fugazzeta (pending) advances. Margarita stays cooking.
- If the cook then clicks the card in "En Horno" tab, it calls `progress_to_ready()` — but only lines with `state === 'cooking'` advance. So only Margarita goes to ready. Fugazzeta stays cooking. Empanada stays cancelled.

**Risk:** The cook sees a card in two tabs and may think advancing it in one tab advances everything. They might deliver a pizza with only 1 of 3 items marked ready.

### 4.2 Optimistic Update Failure During Undo Window

**Scenario:** Cook taps card in "Pendiente" tab → card optimistically moves to "En Horno". The ORM call to `progress_to_cooking()` fails (network blip, server crash, concurrent modification). The undo toast shows for 5 seconds.

**What happens:**
- The card stays in the "En Horno" tab visually (optimistic state)
- If the cook leaves it alone, after the ORM call fails, the catch block restores `prevState` and sets `syncError = true`
- A `!` indicator appears on the card
- **But:** if the cook taps "DESHACER" during the 5s window, the undo action calls `revert_to_previous()` — a server call against a ticket that never actually changed state on the server. This could succeed silently (no-op) or fail with a traceback.

**Risk:** The undo handler calls the reverse method regardless of whether the forward method actually succeeded. If the forward call failed AND the undo is pressed, two things happen: (a) locally the state is already restored by undo, (b) the server gets a `revert_to_previous()` call on a ticket still in `pending` state, which hits the `reverse_map` lookup for `pending` → `not new_state` → returns without action. Silent inconsistency.

### 4.3 Cancel-Undo Race Condition

**Scenario:** Cook cancels a ticket. `cancelTicket()` sets `_pendingCancels` for the order, then fires the ORM call. While the call is in-flight, the 30s auto-refresh fires `loadTickets()` which calls `_reloadOrderTickets()`. That function checks `_pendingCancels` and skips the reload — good. But the bus notification from another device's action also arrives and calls `_reloadOrderTickets()` — also skipped via `_pendingCancels`.

**What happens:**
- The `finally` block clears `_pendingCancels` after the ORM call completes
- If the cancel call itself triggers a server-side bus notification that arrives after `_pendingCancels` is cleared, the ticket reappears briefly before the final `loadTickets()` catches up

**Risk:** Brief visual flicker where a cancelled ticket reappears for one render cycle. Low severity but confusing to cooks during rush.

### 4.4 Note Modification Without Delta Ticket

**Scenario:** Waiter changes a pizza note from "Sin cebolla" to "Sin cebolla, sin ajo" for a line already sent to kitchen (`qty_sent_to_kitchen = 2`).

**What happens:**
- `create_delta_tickets()` detects `note_changed` → updates note in-place on the existing kitchen line, sets `note_modified = True`
- The line keeps its `qty_sent_to_kitchen` at 2, and the note text updates
- The KDS displays a "MODIFICADO" badge with an "OK" acknowledge button
- **BUT:** If the note change happens SIMULTANEOUSLY with a qty change (e.g., waiter changes both note and qty in one save), the note is updated in-place AND a delta ticket is created. The delta ticket's line will have the NEW note text, but the old line's `note_snapshot` was already updated to the new value. This means the delta ticket line carries a duplicate representation.

**Risk:** The merged card in `get_details()` uses `_add_line()` with `seen_pol_ids` dedup on `pos_order_line_id`. The in-place note update changes the original line's note. The delta ticket creates a NEW line for the same `pos_order_line_id` — but `_add_line` skips it because `pid in seen_pol_ids` (already seen from base ticket). The delta qty is lost. **Orders with note+qty changes happening together silently lose the qty delta.**

### 4.5 Ghost/Delivery Card Not Synced Across Tabs

**Scenario:** CookA marks a pizza as delivered → card ghosts for 10s with fade-out animation. During those 10 seconds, CookB on another KDS screen also has the "Entregado" tab open. The bus notification fires `pos_order_delivered`. CookB's screen calls `_reloadOrderTickets()` for the targeted order.

**What happens:**
- CookA's screen: the card is in `ghostingTickets` Set → `_recomputeDerived()` filters it out of `sortedTickets` → but keeps it rendered via `kds-card--ghosting` CSS class
- After 10s, `setTimeout` removes from `ghostingTickets` and calls `loadTickets()` → full reload removes the card
- CookB's screen: `_reloadOrderTickets()` merges fresh data into `this.state.tickets`. If the order is now in `delivered` state and the active tab is NOT "delivered", the card disappears immediately (no ghost animation). If the active tab IS "delivered", the card appears with no "isNew" flag → no chime/vibrate.

**Risk:** Inconsistent UX between screens. CookA sees graceful fade, CookB sees abrupt disappearance or appearance. In a busy kitchen, this causes double-checking ("did that order just appear?").

---

## 5. Additional Architectural Risks

### 5.1 Missing Printer Model Dependency

`pos_kitchen_ticket.py:251` calls `self.env["kitchen.ticket.printer"].print_ticket(self, ...)`. The model `kitchen.ticket.printer` is not defined anywhere in this module. Clicking "Imprimir" will raise `ValueError: External ID not found in the system: kitchen.ticket.printer`. This is a hard crash.

### 5.2 Bus Channel Name Drift

The bus channel is constructed independently in Python (`pos_kitchen.{config_id}` in `pos_kitchen_sync.py:14`) and JavaScript (`pos_kitchen.${shopId}` in `kitchen_screen.js:65`). If either changes without the other, real-time push silently breaks. There is no shared constant or config key.

### 5.3 No Line State Snapshot for Cancel Undo

When `cancelTicket()` cancels all lines, the undo handler at `kitchen_screen.js:611-621` contains a comment: "We don't have per-line previous state stored, so just reload". The undo for a ticket cancel successfully restores the ticket state but ALL lines restart at `pending` — even lines that were `cooking` or `ready` before the cancel. **Cancelling a ticket and undoing resets all line progress.**

### 5.4 Client-Side Oven Capacity Hardcode

`kitchen_screen.js:9` has `const OVEN_CAPACITY = 6`. The server has `kitchen.screen.oven_capacity` (default 6, configurable). The JS uses `this.state.ovenCapacity` which is initialized to `OVEN_CAPACITY` but never syncs from the server. `loadTickets()` does not update `this.state.ovenCapacity` from the server response. **If an admin changes oven capacity on the server, the KDS display still shows 6.**

### 5.5 Sort Instability

`_sortByAge()` at `kitchen_screen.js:384-389` sorts by `Date` objects. Cards with identical `create_date` values (created in the same millisecond) have undefined sort order. In a busy restaurant where multiple orders are placed simultaneously, cards can jump positions on each `_recomputeDerived()` call. No tiebreaker (e.g., by ID) is used.

### 5.6 Single-Document VisibilityChange

`kitchen_screen.js:108-114` adds a `visibilitychange` listener that reloads all tickets when the tab becomes visible. If the KDS is opened in multiple browser tabs/windows, switching between them triggers unnecessary full reloads. Combined with the 30s auto-refresh, this creates redundant server load.

---

## 6. State Management Architecture

### Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     KDS FRONTEND (Owl 2)                        │
│                                                                 │
│  useState({                    useState({                       │
│    tickets: [],          ←────   stages: 'pending',             │
│    sortedTickets: [],    ←────   counts: {...},                 │
│    prepSummary: [],      ←────   stations: [],                  │
│    ghostingTickets,      ←────   activeStation: 'all',          │
│    transitioningTickets, ←────   ovenCapacity, ovenAvailable,  │
│    undoToast,                  audioAlertActive,                │
│    syncError flags,            isLoading,                      │
│    optimistic flags,           prepExpanded,                    │
│    _pendingCancels,            showOvenQueue,                   │
│  })                         })                                  │
│                                                                 │
│  3 update pipelines:                                            │
│  1. loadTickets() → _recomputeDerived()                         │
│  2. Bus notification → _reloadOrderTickets() → _recomputeDerived│
│  3. User action → optimistic mutation → ORM call → reconcile    │
│                                                                 │
│  All 3 pipelines write to the SAME tickets array.               │
└─────────────────────────────────────────────────────────────────┘
```

### Problems with Current Architecture

1. **Single reactive blob**: All state is in one `useState` object. Any mutation triggers a full re-render cascade even if only `undoToast` changed.

2. **Optimistic mutations mutate server data in-place**: `ticket.state = next` directly modifies the object returned from the ORM. If the server call fails, the catch handler must remember and restore previous values. There's no immutable snapshot.

3. **No deduplication of update sources**: The 30s poll, bus notifications, visibility changes, and user actions all write to the same array. A bus notification arriving during a user's undo window causes reconciliation complexity (hence `_pendingCancels`).

4. **Transient UI state mixed with domain data**: `ghostingTickets`, `transitioningTickets`, `optimistic`, and `syncError` are Set/boolean properties bolted onto ticket objects. They are never persisted server-side but live alongside domain data in the same reactive tree.

5. **No optimistic concurrency control**: If two cooks on different screens advance the same ticket simultaneously, both get bus notifications. The last notification wins. There's no version counter or ETag to detect conflicts.

### Proposed: Event-Sourced Command Pattern

A cleaner architecture would separate concerns into distinct layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMMAND LAYER                                │
│  advanceTicket(id) → command → POST /kitchen/ticket/{id}/advance │
│  cancelLine(id)   → command → POST /kitchen/line/{id}/cancel    │
│                                                                  │
│  Each command returns: { accepted: true, version: 27 }          │
│  or: { conflict: true, serverState: {...} }                     │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌───────────────────┐    ┌───────────────────────────────────────┐
│  OPTIMISTIC QUEUE │    │  PROJECTION (read-only derived state)  │
│  Pending commands │    │                                        │
│  with version #   │    │  tickets: Map<id, TicketCard>          │
│  Retry/rollback   │    │  stages: { pending: [...], ... }       │
└───────────────────┘    │  prepSummary: Map<product, count>      │
                          │  ovenQueue: { available, waiting }     │
                          │  ui: { toast, audio, activeTab }       │
                          └───────────────────────────────────────┘
                                     │
                                     ▼
                          ┌───────────────────┐
                          │  UPDATE SOURCES   │
                          │  · 30s poll       │─── merge strategy
                          │  · Bus events     │─── merge strategy
                          │  · Visibility     │─── merge strategy
                          └───────────────────┘
```

**Key design decisions:**

| Concern | Current | Proposed |
|---------|---------|----------|
| State shape | Single blob with mutable objects | Immutable projection derived from source stream |
| Optimistic updates | Mutate ticket object in-place, catch handler restores | Queue of pending commands; reconcile on server response |
| Bus + poll dedup | `_pendingCancels` Set, ad-hoc skipping | Version-counter on each ticket; discard stale updates |
| Transient UI (ghost, transition) | Sets mutated on ticket objects | Separate `ui` substore, never touches domain data |
| Error recovery | Catch block restores prevState | Command queue with retry + exponential backoff |
| Concurrent edits | Last-write-wins (no detection) | Version counter; reject with conflict payload |

### Concrete Implementation Sketch

```javascript
// --- Store (single source of truth, derived immutably) ---
function createKitchenStore() {
    const state = reactive({
        tickets: [],           // sorted, filtered, ready for render
        counts: {},
        prepSummary: [],
        ovenQueue: { available: 0, capacity: 6, waiting: 0 },
        ui: {
            activeStage: 'pending',
            activeStation: 'all',
            toast: null,       // { message, undoCommand, expiresAt }
            audioActive: false,
            ghosting: new Set(),
            transitioning: new Set(),
        },
    });

    // Single pipeline: source events → reducer → projection
    function reduce(action) {
        switch (action.type) {
            case 'TICKETS_LOADED':
                // Merge action.tickets into state.tickets,
                // preserving ghosting/transitioning flags
                break;
            case 'COMMAND_ACCEPTED':
                // Remove from optimistic queue, apply server version
                break;
            case 'COMMAND_REJECTED':
                // Rollback optimistic update, show conflict UI
                break;
        }
    }

    return { state, reduce };
}
```

**Benefits:**
- Single update path eliminates race conditions between poll/bus/user
- Version counters enable proper conflict detection
- Transient UI state never pollutes domain data
- Commands are idempotent and retryable
- Easier to test (pure reduce functions)

**Trade-offs:**
- Increases code volume (~2x more files)
- Requires server-side version tracking (DB migration needed)
- Command queue adds complexity for simple single-user scenarios

---

## 7. Summary of Critical Bugs

| # | Bug | Severity | File:Line |
|---|-----|----------|-----------|
| 1 | `kitchen.ticket.printer` model not found → hard crash on print | **HIGH** | `pos_kitchen_ticket.py:251` |
| 2 | Note+qty simultaneous change silently drops delta qty | **HIGH** | `pos_kitchen_ticket.py:638-651` + `get_details` merge |
| 3 | Cancel+undo resets all line states to pending | **MEDIUM** | `kitchen_screen.js:611-621` |
| 4 | Oven capacity hardcoded in JS, never synced from server | **MEDIUM** | `kitchen_screen.js:9,82` |
| 5 | Bus channel name drift risk (no shared constant) | **MEDIUM** | `pos_kitchen_sync.py:14` vs `kitchen_screen.js:65` |
