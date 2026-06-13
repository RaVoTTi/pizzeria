what is the best flow for a pizzeria? What should I do for 'Review what happens when an order is modified and then canceled'?
1.
Test the flow
✓
Test the flow: create order → modify it → cancel it, check if stock/printer works correctly
2.
Code review
Review the code to ensure delta tickets (additions/cancellations) work properly
3.
Both
Both: review code AND test the flow
4.
Type your own answer

For a **pizzeria**, I would pick **3. Both**, but I'd structure it in a very specific way because cancellations and modifications are operationally critical.

## Why this matters

In a pizza restaurant:

* A pizza may already be in the oven when someone modifies the order.
* An item may have already been printed in the kitchen.
* Ingredients may already be deducted from stock.
* Waiters may accidentally duplicate or cancel items.
* Delivery orders are frequently edited (change drink, remove toppings, add dessert).

If delta tickets or cancellations are wrong, the kitchen gets confused and you can end up making food twice or not charging customers correctly.

---

# Recommended flow to test

### Scenario 1 – Before anything is prepared

1. Create order:

   * 1 Margherita
   * 1 Coke

2. Modify:

   * Remove Coke
   * Add Sprite

3. Cancel entire order.

Expected:

* No kitchen confusion.
* Stock restored correctly.
* No remaining order lines.
* No pending tickets.

---

### Scenario 2 – Kitchen already received ticket

1. Create order:

   * 1 Margherita

2. Send to kitchen.

3. Modify:

   * Add 1 Coke.

Expected:
Kitchen should receive only:

```
+ Coke x1
```

Not:

```
Margherita
Coke
```

because reprinting the entire order causes duplicate preparation.

---

### Scenario 3 – Remove an item after sending

1. Send:

   * Margherita
   * Coke

2. Remove Coke.

Expected:
Kitchen receives:

```
- Coke x1
```

This is extremely important because staff need to know they should not prepare or deliver the Coke.

---

### Scenario 4 – Cancel entire order after sending

1. Send:

   * Margherita
   * Coke

2. Cancel order.

Expected:
Kitchen receives:

```
CANCEL ORDER
Margherita x1
Coke x1
```

or

```
- Margherita x1
- Coke x1
```

depending on your workflow.

---

# What to verify in code

### Stock

Questions:

* Is stock deducted immediately?
* On payment?
* On validation?
* On kitchen send?

Then verify:

```text
Create → Modify → Cancel
```

does:

```text
Stock deducted
→ adjustments applied
→ stock restored
```

No negative inventory.

---

### Kitchen tickets

Verify that:

```text
new_qty - old_qty
```

is calculated correctly.

Example:

```
Old: Pizza x2
New: Pizza x3

Delta:
+ Pizza x1
```

Example:

```
Old: Pizza x2
New: Pizza x1

Delta:
- Pizza x1
```

---

### Printer logic

Ensure printer sends:

* additions
* removals
* cancellations

instead of printing the whole order every time.

---

# What I would implement for a real pizzeria

```
Draft
↓
Send to Kitchen
↓
Kitchen Accepted
↓
Prepared
↓
Served/Delivered
↓
Paid
```

Modification rules:

| State    | Allow modifications? | Action                         |
| -------- | -------------------- | ------------------------------ |
| Draft    | Yes                  | Silent update                  |
| Sent     | Yes                  | Delta ticket                   |
| Accepted | Limited              | Manager confirmation           |
| Prepared | Rarely               | New order or cancellation flow |
| Paid     | No                   | Refund process                 |

---

For a pizzeria, the most dangerous bug is:

> Customer removes an item after it was sent, and the kitchen never receives the cancellation.

That leads directly to wasted food and inventory discrepancies.

So my recommendation would be:

1. **Review the code first** to understand how deltas are generated.
2. **Test every create → modify → cancel scenario**.
3. **Specifically verify kitchen tickets and stock restoration**, because those are usually where POS systems fail.

yes but the coke doesn't modify anything from the kitchen

Exactly. In a pizzeria, you should think in terms of **kitchen-relevant modifications** and **non-kitchen modifications**.

### Kitchen-relevant changes

These should generate delta tickets:

* Add Pizza → `+ Pizza x1`
* Remove Pizza → `- Pizza x1`
* Add extra cheese → `+ Extra Cheese`
* Change toppings → cancellation + addition, or a modification note
* Add empanada → `+ Empanada x1`

### Non-kitchen changes

These should **not** generate kitchen tickets:

* Add Coke (if beverages are not prepared in kitchen)
* Remove Coke
* Change customer name
* Change payment method
* Add delivery instructions
* Change table number (usually)

---

For your review, I would test something like this:

### Test 1

```
Create:
- Pizza x1

Send to kitchen.

Modify:
+ Coke x1
```

Expected:

```
No kitchen ticket printed.
No KDS update.
```

---

### Test 2

```
Create:
- Pizza x1

Send to kitchen.

Modify:
+ Pizza x1
```

Expected:

```
Kitchen receives:
+ Pizza x1
```

---

### Test 3

```
Create:
- Pizza x1
- Coke x1

Send.

Modify:
- Coke x1
```

Expected:

```
No kitchen ticket.
```

---

### Test 4

```
Create:
- Pizza x1
- Coke x1

Send.

Cancel order.
```

This one depends on your business rules:

**Option A (recommended):**
Kitchen receives:

```
CANCEL
Pizza x1
```

Coke is ignored.

**Option B:**
Cancel everything, but only print kitchen products.

---

From a code perspective, the logic should be something like:

```python
for line in order_lines:
    if line.product_id.pos_categ_id in kitchen_categories:
        generate_delta(line)
```

or

```python
if line.product_id.is_kitchen_product:
    generate_delta(line)
```

The key idea is:

> The kitchen system should react only to products that require preparation. Drinks like Coke should be completely invisible to the kitchen workflow if they are not prepared there.

So when reviewing **"modify then cancel"**, I would specifically ask:

1. Does modifying a non-kitchen item trigger unnecessary kitchen tickets?
2. Does canceling an order only cancel kitchen items?
3. Can non-kitchen products accidentally affect KDS state or printer logic?

Those are the bugs that usually appear in POS/KDS implementations.
