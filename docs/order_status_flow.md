# Order Status Flow — Pizzeria El Gordo

## Overview

This document describes the complete order lifecycle from POS creation to kitchen delivery, including state transitions, notifications, and delta ticket handling.

---

## Order Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              POS (Frontend)                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. CREATE ORDER                                                        │
│     • Cashier adds products (pizzas, drinks, etc.)                      │
│     • Sets order type: Mesa / Delivery / Retira                         │
│     • Optional: Set requested time (Hora button)                        │
│     • Optional: Add customer notes                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. CONFIRM ORDER (Click "Kitchen" button)                              │
│     • POS calls: pos.order.process_order_for_kitchen()                  │
│     • Server creates: pos.kitchen.ticket (type="new", batch="A")        │
│     • Only kitchen-relevant products are included (pos_categ_ids match) │
│     • Non-kitchen items (drinks) are excluded                           │
│     • Bus notification: pos_order_created                               │
│     • KDS updates in real-time                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         KITCHEN DISPLAY (KDS)                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. PENDING → COOKING (Tap ticket or line)                              │
│     • Kitchen staff taps the ticket card                                │
│     • State: pending → cooking                                          │
│     • started_at timestamp is set                                       │
│     • Bus notification: pos_order_accepted                              │
│     • Optional: Print ticket to thermal printer                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. COOKING → READY (Tap ticket or line)                                │
│     • Kitchen staff taps when food is ready                             │
│     • State: cooking → ready                                            │
│     • ready_at timestamp is set                                         │
│     • All lines marked as ready                                         │
│     • Bus notification: pos_order_completed                             │
│     • SLA timer turns green                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. READY → DELIVERED (Tap ticket)                                      │
│     • Waiter picks up the order                                         │
│     • State: ready → delivered                                          │
│     • delivered_at timestamp is set                                     │
│     • Bus notification: pos_order_delivered                             │
│     • Ticket fades out (ghost effect, 10s)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  6. PAYMENT (POS)                                                       │
│     • Customer pays (cash, card, Mercado Pago)                          │
│     • POS calls: pos.order.action_pos_order_paid()                      │
│     • All related tickets: payment_status = "paid"                      │
│     • KDS badge updates: "NO PAGO" → "PAGADO"                           │
│     • Stock deducted via phantom BoM (automatic)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Ticket States

| State      | Spanish     | Description                                      |
|------------|-------------|--------------------------------------------------|
| `pending`  | Pendiente   | Order received, waiting for kitchen to start     |
| `cooking`  | En Horno    | Kitchen is preparing the food                    |
| `waiting`  | Esperando   | Waiting for oven space (not currently used)      |
| `ready`    | Listo       | Food is ready for pickup                         |
| `delivered`| Entregado   | Food has been delivered to customer              |
| `cancelled`| Cancelado   | Order/ticket was cancelled                       |

---

## Delta Tickets (Modifications)

When an order is modified **after** being sent to the kitchen, delta tickets are created:

### Addition (qty increased)

```
Original: Pizza x1
Modified: Pizza x2

Delta ticket created:
  type: "addition"
  batch_letter: "B" (next available)
  line: Pizza x1 (the difference)
```

### Cancellation (qty decreased)

```
Original: Pizza x2
Modified: Pizza x1

Delta ticket created:
  type: "cancellation"
  batch_letter: "C" (next available)
  line: Pizza x1 (state: cancelled)
```

### Non-Kitchen Items

Items not in kitchen categories (e.g., drinks) do **not** generate delta tickets:

```
Original: Pizza x1, Coke x1
Modified: Pizza x1, Coke x2

Result:
  ✓ No delta ticket (Coke is not a kitchen item)
  ✗ Kitchen is not notified
```

---

## Batch Letters

Each ticket gets a unique batch letter (A-Z):

- **A** = Original order
- **B, C, D...** = Additions or cancellations

Example:
```
Order #0001A: Pizza Margherita x1 (original)
Order #0001B: + Coke x1 (addition - but not sent to kitchen)
Order #0001C: + Pizza Pepperoni x1 (addition)
Order #0001D: - Pizza Margherita x1 (cancellation)
```

---

## Notifications (Bus Events)

| Event                    | Trigger                          | KDS Action              |
|--------------------------|----------------------------------|-------------------------|
| `pos_order_created`      | New ticket or delta created      | Load tickets, play chime|
| `pos_order_accepted`     | Ticket moved to cooking          | Update state            |
| `pos_order_completed`    | Ticket moved to ready            | Update state            |
| `pos_order_delivered`    | Ticket moved to delivered        | Update state, ghost     |
| `pos_order_cancelled`    | Ticket cancelled                 | Update state            |
| `pos_order_paid`         | Payment completed                | Update payment badge    |
| `pos_order_line_cooking` | Individual line moved to cooking | Update line state       |
| `pos_order_line_ready`   | Individual line moved to ready   | Update line state       |
| `pos_order_line_cancelled`| Individual line cancelled       | Update line state       |

---

## SLA Tracking

The KDS tracks order age with color-coded badges:

| Time      | Color  | Meaning                    |
|-----------|--------|----------------------------|
| < 10 min  | Green  | Normal                     |
| 10-30 min | Amber  | Warning                    |
| > 30 min  | Red    | Urgent (prep summary highlights) |

---

## Oven Queue

The KDS shows available oven slots:

```
Espacio en horno: 4/6 — 2 esperando
```

- **4/6** = 4 slots available out of 6 capacity
- **2 esperando** = 2 tickets waiting for oven space

Oven capacity is configurable in `kitchen.screen.oven_capacity` (default: 6).

---

## Stock Handling

Stock is handled by Odoo's phantom BoM system:

1. **On order creation**: No stock deduction yet
2. **On payment**: Phantom BoM explodes, deducting raw ingredients (flour, cheese, etc.)
3. **On cancellation**: Stock is restored (Odoo handles this automatically)

**Important**: Kitchen tickets do NOT control stock. They are purely for kitchen workflow management.

---

## Printer Integration

### Kitchen Tickets (KDS → Thermal Printer)

- Triggered by: KDS "Imprimir" button on ticket card
- Format: ESC/POS raw commands
- Printer: CUPS via `lp -d <printer> -o raw`
- Includes: Logo, order details, category grouping, notes, total

### Customer Receipts (POS → Thermal Printer)

- Triggered by: POS "Print Receipt" button
- Format: Same as kitchen ticket (via `print_customer_receipt()`)
- Printer: Same CUPS printer

---

## Cancellation Flow

### Cancel Individual Line

1. Kitchen staff taps the "X" button on a line
2. Line state: current → cancelled
3. Bus notification: `pos_order_line_cancelled`
4. KDS updates immediately

### Cancel Entire Ticket

1. Kitchen staff taps "Cancelar Ticket" button
2. Ticket state: current → cancelled
3. All lines marked as cancelled
4. Bus notification: `pos_order_cancelled`
5. KDS removes ticket from active view

### Cancel Order (POS)

1. Cashier cancels the order in POS
2. `pos.order` state changes
3. Related tickets should be cancelled (manual or automatic)
4. Stock is restored

---

## Edge Cases

### Order Modified After Cooking Started

- Delta tickets are still created
- Kitchen sees the addition/cancellation
- **Business rule**: Kitchen staff should check if item is already in oven before acting

### Payment Before Kitchen Finishes

- `payment_status` updates to "paid"
- Badge changes: "NO PAGO" → "PAGADO"
- Kitchen continues working (payment doesn't affect cooking flow)

### Multiple Tickets for Same Order

- Original ticket (batch A)
- Addition ticket (batch B)
- Cancellation ticket (batch C)
- All linked to same `pos.order`
- KDS shows all active tickets

---

## Testing Checklist

- [ ] Create order → Kitchen receives ticket
- [ ] Modify order (add item) → Delta ticket created
- [ ] Modify order (remove item) → Cancellation ticket created
- [ ] Non-kitchen item modified → No delta ticket
- [ ] Cancel order → All tickets cancelled
- [ ] Payment → Badge updates to "PAGADO"
- [ ] Print ticket → Thermal printer receives ESC/POS
- [ ] SLA timer → Color changes based on age
- [ ] Oven queue → Shows available slots correctly
