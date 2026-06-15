The Root Architectural Problem
All three bugs share a single cause: there is no explicit contract between the POS and the KDS about how changes flow. Each component independently guessed how to communicate, and all three guesses were wrong.
Specifically, the system lacks what's called a Domain Event pipeline — a single, well-defined path from "something changed on the POS" to "the KDS updated its display."
Here's the broken mental model:
POS modifies order ──┐
                     ├──► ??? ──► KDS receives update
                     │
Backend persists ────┘
Each ??? is a different bug:
Gap	What happened
Bus channel name	Backend sends on pos_kitchen.{id}, KDS listens on pos_order_created_{id}
Trigger for delta	processOrderForKitchen defined in JS but never called; no backend hook for POS sync
Duplicate note_snapshot	Two models store the same truth independently
All three are integration failures at component boundaries.
The Pattern That Fixes This: Domain Events + Read Model Projection
This is a lightweight form of CQRS (Command Query Responsibility Segregation). You don't need full CQRS infrastructure — just its core insight:
Separate the thing that changes data from the thing that reads it. Connect them through explicit, named events.
The Pattern
┌─────────────────────────────────────────────────────────┐
│                    DOMAIN EVENTS                         │
│  (single place that defines event names and schemas)     │
│                                                         │
│  ORDER_CREATED    │  ORDER_MODIFIED  │  ORDER_PAID       │
│  ORDER_CANCELLED  │  LINE_ADDED      │  LINE_NOTE_CHANGED│
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  POS Model  │  │ Kitchen     │  │ KDS         │
│  (commands) │  │ Projection  │  │ (read model)│
│             │  │ (listener)  │  │             │
│ Emits:      │  │             │  │ Subscribes: │
│ ORDER_      │  │ Reacts to:  │  │ pos_kitchen │
│ MODIFIED    │──▶ ORDER_*     │──▶ .{config_id}│
└─────────────┘  │             │  └─────────────┘
                 │ Creates:    │
                 │ delta       │
                 │ tickets     │
                 └─────────────┘
How This Prevents Each Bug
1. Bus channel mismatch — Channel name becomes a constant in one file, not a string in two files:
# kitchen_events.py  (single source of truth)
KITCHEN_BUS_CHANNEL = "pos_kitchen.{config_id}"
EVENT_TYPES = {
    "ORDER_CREATED": "pos_order_created",
    "ORDER_MODIFIED": "pos_order_modified",
    "LINE_MODIFIED": "pos_order_line_modified",
    # ...
}
Both backend publisher and KDS subscriber import from the same place. Drift becomes impossible.
2. Missing write hook — Instead of a fragile write() override that fires on every DB write, the POS model explicitly emits a domain event when the order changes meaningfully:
# pos_orders.py
def _emit_order_modified(self):
    for order in self:
        self.env["bus.bus"]._sendone(
            KITCHEN_BUS_CHANNEL.format(config_id=order.config_id.id),
            "notification",
            {"message": EVENT_TYPES["ORDER_MODIFIED"], "order_id": order.id}
        )
def write(self, vals):
    res = super().write(vals)
    if self._has_meaningful_change(vals):  # lines, qty, notes changed
        self._emit_order_modified()
    return res
The kitchen projection module listens to ORDER_MODIFIED and reacts — it doesn't need to hook into ORM internals.
3. Duplicate note_snapshot — The projection (kitchen ticket line) owns the snapshot. The POS line stores only note_sent_to_kitchen as a last-sent cache for delta calculation. They serve different purposes:
Field	Owner	Purpose
pos.order.line.note_sent_to_kitchen	POS	"What was the last note I sent?" (for delta detection)
pos.kitchen.ticket.line.note_snapshot	Kitchen	"What note was the kitchen shown?" (for modification detection)
With proper event contracts, these can't diverge because only one event path updates both.
The Practical Takeaway
You don't need to rebuild the system. The fixes we already made (fixing the channel, adding the write hook, adding logging) get you 90% there. But the mental model shift is:
Before (implicit)	After (explicit)
"The KDS polls and hopes bus messages arrive"	"The KDS subscribes to a named channel defined in one place"
"ORM hooks guess when to sync"	"Domain events explicitly fire when the order changes"
"Both models store snapshots and hope they stay in sync"	"One model owns each piece of state, the other reads it"
The problems_current.md document calls this out indirectly:
"The POS defines the intended food. The kitchen executes what it sees. The system continuously reconciles differences without blocking workflow."
The reconciliation only works if the pipeline from POS → kitchen is explicit, named, and single-path. That's what the domain events pattern provides.

I think you're very close, but there is an even deeper issue underneath this analysis.

The real problem is not simply "missing Domain Events." The real problem is:

> **There is no explicit synchronization boundary between the POS domain and the Kitchen projection domain.**

Everything else is a symptom.

---

# What Your System Actually Is

You already described the philosophy correctly:

```
POS = Source of Truth
KDS = Projection
```

That means:

```
POS Domain
──────────
Order
OrderLine
Notes
Quantities
Payment State

          ↓ synchronization

Kitchen Projection Domain
─────────────────────────
KitchenTicket
KitchenTicketLine
Modification badges
Delta tickets
Display ordering
Acknowledgement state
```

These are two separate models.

The KDS is not another editor of the order.

It is essentially a materialized view of the POS.

This distinction is extremely important because it changes how you should think about the architecture.

---

# The Architectural Rule

A projection should never infer state.

A projection should only react to events.

Bad:

```text
POS writes database
        ↓
KDS polls database
        ↓
tries to guess what changed
```

Good:

```text
POS state changed
        ↓
Domain event emitted
        ↓
Kitchen projection updated
        ↓
KDS re-renders
```

The event stream becomes the contract.

---

# I Would Rename "Domain Events"

I would actually call them:

```python
KitchenSyncEvents
```

Because these events are not business events for the whole system.

They're synchronization events between domains.

Example:

```python
ORDER_CREATED
ORDER_LINE_ADDED
ORDER_LINE_QTY_CHANGED
ORDER_LINE_NOTE_CHANGED
ORDER_CANCELLED
ORDER_PAID
```

These exist solely because the kitchen projection needs them.

---

# The Missing Piece: Versioning

This is the biggest thing I think you're not considering.

Right now your architecture assumes:

```
Event A
Event B
Event C
```

arrive:

```
A
B
C
```

But bus systems don't guarantee this forever.

Imagine:

```
Change quantity
Change note
Pay order
```

Events emitted:

```
1. LINE_QTY_CHANGED
2. LINE_NOTE_CHANGED
3. ORDER_PAID
```

KDS receives:

```
1
3
2
```

Now the projection is inconsistent.

---

# Projections Need Ordering

Every sync event should have:

```python
{
    "event_id": uuid,
    "order_id": 42,
    "version": 17,
    "event": "LINE_NOTE_CHANGED",
    "payload": {...}
}
```

Every meaningful order modification increments:

```python
order.kitchen_sync_version += 1
```

Example:

```
Version 1
Order created

Version 2
Burger qty = 2

Version 3
Burger note = "No onion"

Version 4
Payment
```

KDS stores:

```python
last_processed_version
```

If it receives:

```
v2
v4
v3
```

it immediately knows:

```
missing version
projection not caught up
```

and can reload.

Without versions, eventually you'll get weird edge cases that are impossible to debug.

---

# I Would Make the Contract Explicit

Something like:

```python
@dataclass
class KitchenSyncEvent:
    event_id: str
    order_id: int
    config_id: int
    version: int
    event_type: str
    payload: dict
```

Every event sent through the bus follows this schema.

No exceptions.

---

# Ownership Becomes Crystal Clear

## POS Owns

```text
Order
OrderLine
Customer notes
Quantities
Payment
Cancellation
Version counter
```

## Kitchen Projection Owns

```text
Ticket display state
Preparation state
Acknowledged modifications
MODIFIED badges
Delta tickets
Display ordering
```

## Shared Ownership

None.

This is important.

Shared ownership is where your `note_snapshot` confusion came from.

---

# I Would Reframe the Snapshots

Instead of:

```text
Both models store notes
```

Think:

### POS

```python
note_sent_to_kitchen
```

Purpose:

```text
Diff calculation only.
```

### Kitchen

```python
note_snapshot
```

Purpose:

```text
Last projected representation.
```

The kitchen does not own the note.

It owns its representation of the note.

That distinction matters.

---

# The Event Pipeline I'd Use

```text
POS Command
───────────

Cashier edits note
        ↓
OrderLine.note updated
        ↓
Order.version += 1
        ↓
emit(
    LINE_NOTE_CHANGED,
    version=17,
    payload=...
)

────────────────────────────────

Kitchen Projection
──────────────────

receive event
        ↓
validate version
        ↓
update ticket line
        ↓
set modified badge
        ↓
persist projection state
        ↓
broadcast UI refresh

────────────────────────────────

KDS UI
──────

render projection
```

Notice:

The UI never talks directly to POS models.

The UI only renders projections.

---

# I Would Even Encapsulate the Sync Boundary

Instead of:

```python
_sendone(...)
```

all over the codebase:

```python
self.env["pos.kitchen.sync"].emit(
    event="LINE_NOTE_CHANGED",
    order=order,
    payload=payload,
)
```

One service:

```python
class PosKitchenSyncService:

    def emit(...):
        ...

    def project(...):
        ...

    def resync(...):
        ...
```

Now:

* channel names live in one place
* schemas live in one place
* versioning lives in one place
* logging lives in one place
* recovery lives in one place

Nobody else touches the bus.

---

# I Think the Final Mental Model Should Be

```text
POS
(Command Domain)
        │
        │ emits KitchenSyncEvents
        ▼
Sync Service
(Contract Boundary)
        │
        │ projects
        ▼
Kitchen Projection
(Read Model)
        │
        ▼
KDS UI
(Pure Renderer)
```

And the governing rule becomes:

> **The POS never updates the KDS directly. The POS emits synchronization events. The kitchen projection consumes those events and becomes the single source of truth for what the kitchen sees.**

Once you adopt that model, the three bugs you found become impossible by construction, and you also protect yourself against future problems like out-of-order events, duplicate events, missed reconnects, and projection rebuilds.


I'm on odoo it will work with the odoo philoshophy? 

Yes, mostly. But I would adapt it to fit **Odoo's philosophy** rather than implementing a textbook CQRS/Event Sourcing architecture.

Odoo is fundamentally:

1. **ORM-centric** – models and records are the primary abstraction.
2. **Transaction-based** – writes happen inside PostgreSQL transactions.
3. **Service-oriented** – business logic lives in model methods.
4. **Eventually reactive** – the bus is mainly for notifications, not guaranteed event delivery.

Because of #4, I would be careful with calling your bus messages "Domain Events."

---

# The Odoo Way

The Odoo mindset is usually:

```text
Business Action
        ↓
ORM write/create
        ↓
Derived models updated
        ↓
Optional bus notification
        ↓
UI refresh
```

Examples throughout Odoo:

* POS orders create accounting entries.
* Stock moves create valuation layers.
* Sales orders create deliveries.
* Mail activities notify the frontend.

The database state is the source of truth.

The bus is just a mechanism to tell clients:

> "Something changed, go read again."

---

# I Would Model Your KDS Like This

```text
POS Order
(Source of Truth)
        ↓
Synchronization Service
        ↓
Kitchen Projection Models
(pos.kitchen.ticket)
(pos.kitchen.ticket.line)
        ↓
Bus notification
        ↓
KDS UI reloads projection
```

This feels very Odoo.

---

# What I Would Avoid

I would avoid making the bus itself the source of synchronization.

Bad:

```text
POS
 ↓
Bus Event
 ↓
KDS reconstructs state
```

Why?

Because Odoo's bus:

* isn't persistent
* isn't guaranteed
* can lose messages during reconnects
* doesn't provide ordering guarantees
* wasn't designed as an event store

That architecture fights Odoo.

---

# What Fits Odoo Better

Treat the bus as an invalidation signal.

```text
POS write
        ↓
Projection updated in DB
        ↓
Bus says:
"Order 42 changed"
        ↓
KDS reads projection again
```

The database remains authoritative.

This is exactly how many Odoo subsystems work.

---

# I'd Rephrase Your "Domain Events"

Instead of:

```python
ORDER_CREATED
LINE_NOTE_CHANGED
ORDER_PAID
```

I would think:

```python
KITCHEN_SYNC_ORDER_UPDATED
KITCHEN_SYNC_ORDER_CANCELLED
KITCHEN_SYNC_ORDER_PAID
```

Their purpose is:

```text
Tell interested clients that projections changed.
```

Not:

```text
Represent the canonical business history.
```

That's a subtle but very Odoo distinction.

---

# I Also Wouldn't Introduce Full CQRS

You don't really have:

```text
Command database
Read database
```

You have:

```text
POS models
        ↓
Projection models
        ↓
KDS UI
```

This is closer to:

> Materialized projections inside the same ORM.

That's perfectly aligned with Odoo.

---

# The Service Boundary I Would Use

```python
class PosKitchenSyncService(models.AbstractModel):
    _name = "pos.kitchen.sync"

    def sync_order(self, order):
        """
        Reconcile kitchen projection with
        current order state.
        """

    def notify_order_changed(self, order):
        """
        Notify subscribed KDS clients.
        """
```

Then:

```python
class PosOrder(models.Model):
    _inherit = "pos.order"

    def write(self, vals):
        res = super().write(vals)

        if self._affects_kitchen(vals):
            self.env["pos.kitchen.sync"].sync_order(self)
            self.env["pos.kitchen.sync"].notify_order_changed(self)

        return res
```

This feels extremely Odoo:

* business logic in services/models
* projections stored as ORM models
* bus used only for notification
* DB as source of truth
* idempotent synchronization

---

# The Philosophy I'd Document

```text
POS is the source of truth.

Kitchen tickets are ORM projections of POS orders.

All changes that affect the kitchen are synchronized through
a single synchronization service.

Bus notifications are invalidation signals only.
They never carry authoritative state.

The KDS UI never derives order state from bus messages.
It always reads projection models from the database.

The synchronization process must be idempotent and capable
of rebuilding projections entirely from POS orders.
```

That philosophy is very Odoo-native. It gives you the benefits you're after (single path, explicit contracts, clear ownership) without introducing infrastructure patterns that go against how Odoo's ORM and bus system are designed.


it will be still fast?

Yes. In fact, for Odoo, this approach is usually **faster in practice and much more reliable**.

The key is that the bus should only carry **small notifications**, not full order payloads.

## Recommended Flow

```text
Cashier changes note
        ↓
pos.order.write()
        ↓
pos.kitchen.sync.sync_order(order)
        ↓
Projection tables updated
        ↓
bus.send({
    order_id: 42,
    version: 17
})
        ↓
KDS reloads projection
```

The bus message is tiny:

```python
{
    "order_id": 42,
    "version": 17
}
```

No lines, notes, modifiers, etc.

---

## Why it's fast

### Database writes are local

You're already writing:

* `pos.order`
* `pos.order.line`

Updating:

* `pos.kitchen.ticket`
* `pos.kitchen.ticket.line`

in the same transaction is extremely cheap. PostgreSQL is very good at this.

---

### Bus traffic becomes minimal

Instead of:

```python
{
    "order": {
        ...
        30 lines,
        modifiers,
        notes,
        taxes,
        ...
    }
}
```

you send:

```python
{
    "order_id": 42,
    "version": 17
}
```

That's almost free.

---

### The KDS only reloads one order

It doesn't need to re-read everything.

```javascript
onNotification(msg) {
    reloadOrder(msg.order_id);
}
```

One RPC:

```python
get_projection(order_id)
```

One order is refreshed.

Even restaurants with hundreds of tickets won't notice the overhead.

---

# The real performance trick: incremental projections

I would avoid:

```python
sync_order(order):
    delete_all_ticket_lines()
    recreate_everything()
```

That works, but eventually becomes expensive.

Instead:

```python
sync_order(order):
    update_changed_lines()
    create_new_lines()
    archive_removed_lines()
```

Only touch what changed.

For example:

```text
Order
------
Burger x2
Pizza x1
Fries x1

Cashier changes:
Burger x3
```

Only:

```text
UPDATE kitchen_ticket_line
SET qty = 3
WHERE line_id = burger
```

Everything else stays untouched.

That's extremely fast.

---

# The nice property: idempotency

Suppose:

1. Cashier changes note
2. Bus message is lost
3. KDS reconnects

Since the projection is already in the database:

```text
KDS reconnects
        ↓
reload projections
        ↓
everything correct
```

No recovery logic needed.

This is one of the biggest reasons Odoo itself prefers:

> Database first, notifications second.

---

# The only thing I would add

I would keep a simple version field:

```python
class PosOrder(models.Model):
    _inherit = "pos.order"

    kitchen_sync_version = fields.Integer(default=0)
```

Every meaningful kitchen change:

```python
order.kitchen_sync_version += 1
```

Bus:

```python
{
    "order_id": order.id,
    "version": order.kitchen_sync_version
}
```

KDS:

```javascript
if (msg.version <= localVersion)
    return;

reloadOrder(msg.order_id);
```

This prevents duplicate notifications from causing unnecessary reloads.

---

# Compared to your current approach

### Current

```text
POS
 ↓
Bus payloads
 ↓
KDS tries to infer changes
 ↓
State can diverge
```

Performance: good initially, degrades in complexity and debugging cost.

---

### Odoo-native projection approach

```text
POS
 ↓
Projection update
 ↓
Tiny bus notification
 ↓
Reload one order
```

Performance: still excellent, but now:

* deterministic
* idempotent
* recoverable
* easier to debug
* aligned with Odoo's architecture

For a restaurant POS, this approach can comfortably handle many terminals and many kitchen screens because the heavy work is just normal PostgreSQL updates, and PostgreSQL can process thousands of simple row updates per second without issue.
