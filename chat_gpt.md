Creo que la idea se puede ordenar así:

### Problema principal

El problema principal no es la gestión de las comandas en sí, sino **las modificaciones de una comanda que ya está en proceso**.

Por ejemplo:

1. Se envía una mesa con:

   * 2 pizzas
   * 1 hamburguesa

2. La cocina ya empezó a trabajar:

   * Una pizza está en horno.
   * La hamburguesa está en preparación.
   * La otra pizza todavía no comenzó.

3. El cliente modifica el pedido:

   * Agrega una pizza.
   * Cambia ingredientes de la hamburguesa.
   * Cancela una de las pizzas.

En ese momento, no se puede simplemente reenviar la comanda completa, porque:

* Se duplicaría información.
* La cocina no sabría qué es nuevo y qué ya está haciendo.
* Algunos productos pueden estar en estados distintos (preparación, horno, entregado, etc.).

---

### Concepto de "comanda amarilla"

La **comanda amarilla** representa una modificación del pedido original.

No es una nueva comanda completa, sino un **delta** (los cambios realizados).

Debe indicar claramente:

**Agregar**

* +1 Pizza Muzzarella

**Modificar**

* Hamburguesa → sin cebolla

**Cancelar**

* -1 Pizza Napolitana

---

### Estados individuales pero agrupados

La comanda es:

* **Individual**, porque cada producto tiene su propio estado.
* **En conjunto**, porque todos pertenecen a la misma mesa o pedido.

Ejemplo:

**Mesa 12**

* Pizza 1 → En horno
* Pizza 2 → Entregada
* Hamburguesa → En preparación
* Pizza agregada → Pendiente

Todo sigue siendo la misma mesa, pero cada línea tiene un ciclo de vida independiente.

---

### Ventaja de este enfoque

La cocina puede entender inmediatamente:

1. Qué platos ya estaban.
2. Qué platos ya fueron entregados.
3. Qué modificaciones acaban de llegar.
4. Qué productos faltan preparar.
5. Hacia dónde debe ir cada cambio.

La regla conceptual sería:

> **La comanda original representa el estado base del pedido. Las comandas amarillas representan únicamente las diferencias (agregados, modificaciones y cancelaciones) sobre ese estado, manteniendo el seguimiento individual de cada producto, aunque todos sigan perteneciendo al mismo pedido o mesa.**

Creo que esa última frase captura bastante bien la idea de **"es individual pero en conjunto"** que estabas tratando de expresar.


es una pizzeria, pero eso si puede pasar porque por ejemplo cuando vos pones una de roquefort la mandas asi antes de meterla al horno

Ahí cambia bastante el análisis. En una pizzería **sí puede ser válido reenviar la pizza completa**, porque la pizza tiene etapas de producción.

Por ejemplo:

1. Se pide una pizza de muzzarella.
2. El pizzero la arma y está lista para entrar al horno.
3. El cliente dice: "Hacé media roquefort".

En ese momento, la pizza todavía no está terminada. Se puede modificar antes de entrar al horno.

El problema entonces no es simplemente "no reenviar todo", sino **distinguir qué elementos todavía son modificables y cuáles ya cruzaron un punto de no retorno**.

### La verdadera pregunta es el estado de la pizza

Una pizza puede estar:

* Pendiente
* Armándose
* Lista para horno
* En horno
* Lista para entregar
* Entregada

Dependiendo del estado:

| Estado              | ¿Se puede modificar? |
| ------------------- | -------------------- |
| Pendiente           | Sí                   |
| Armándose           | Sí                   |
| Lista para horno    | Sí                   |
| En horno            | Depende del cambio   |
| Lista para entregar | Casi nunca           |
| Entregada           | No                   |

---

### Entonces las comandas amarillas siguen teniendo sentido

Pero ya no representan únicamente "agregados".

También representan:

* Modificaciones permitidas sobre productos existentes.
* Nuevos productos.
* Cancelaciones de productos que todavía no comenzaron.

Ejemplo:

**Mesa 5**

* Pizza Muzzarella → Lista para horno

**Comanda amarilla**

* Pizza Muzzarella → Cambiar a 1/2 Muzzarella + 1/2 Roquefort

El pizzero entiende:

> "No es una pizza nueva. Es la misma pizza, pero cambió antes de entrar al horno."

---

### El concepto "individual pero en conjunto"

Cada pizza es una entidad individual:

* Pizza #1 → En horno
* Pizza #2 → Armándose
* Pizza #3 → Entregada

Pero todas pertenecen al mismo pedido.

Las modificaciones deberían aplicarse a una pizza específica, no al pedido entero.

Porque si enviás nuevamente toda la mesa:

**Mesa 5**

* 2 Muzzarellas

y luego:

**Mesa 5**

* 2 Muzzarellas
* 1 media Roquefort

el pizzero no sabe:

* ¿Hay una pizza nueva?
* ¿Hay que modificar una existente?
* ¿Cuál de las dos pizzas cambió?

---

Creo que la abstracción correcta para el sistema es:

> **Las modificaciones deben aplicarse sobre líneas de pedido individuales (cada pizza) y no sobre la comanda completa. Cada línea tiene un estado de producción que determina si la modificación es posible, debe generar una nueva preparación o debe ser rechazada.**

Eso modela mucho mejor cómo trabaja una cocina de pizzería que una lógica de "reenviar pedido completo" o "nunca reenviar nada".


Lo que yo pensaba porque por ejemplo si vos tocas la card completa pasa al horno pero si tocas el item, los items que tocaste van al horno, y los otros quedarian como en la categoria por preparar, se entiende?

Sí, se entiende, y de hecho me parece una muy buena abstracción para una pizzería.

La idea sería que la **card (comanda)** y los **ítems** tienen acciones diferentes:

### Acción sobre la card completa

La card representa el pedido entero.

Si tocás la card:

```
Mesa 7
- Pizza Muzzarella
- Pizza Especial
- Empanadas
```

Todo pasa de:

**Por preparar → Horno**

La acción significa:

> "Todo este pedido avanza al siguiente estado."

---

### Acción sobre un ítem individual

Cada producto puede avanzar independientemente.

Por ejemplo:

```
Mesa 7
- Pizza Muzzarella        → Horno
- Pizza Especial          → Por preparar
- Empanadas               → Por preparar
```

Solamente la Muzzarella pasó al horno.

La card sigue existiendo porque todavía quedan productos pendientes.

---

### La ventaja de este modelo

Resuelve situaciones reales:

**Caso 1**
El pizzero ya tiene una pizza lista para hornear, pero la otra todavía no está armada.

**Caso 2**
Se agregan productos mientras algunos ya están en horno.

**Caso 3**
Parte del pedido ya fue entregada y otra parte sigue preparándose.

---

### La consecuencia de diseño importante

La card no debería tener un único estado.

Porque podría ocurrir:

```
Mesa 7
✔ Pizza Muzzarella      → Entregada
🔥 Pizza Especial       → Horno
🟡 Empanadas            → Por preparar
```

Entonces la card está en un estado "mixto".

El estado real del pedido es la composición de los estados de sus ítems.

---

### Incluso podrías pensarlo así

**Card = Contenedor**

* Mesa
* Cliente
* Hora
* Notas

**Items = Máquinas de estado independientes**

* Pizza 1 → Por preparar → Horno → Entregada
* Pizza 2 → Por preparar → Horno → Entregada
* Empanadas → Por preparar → Entregadas

La card simplemente agrupa todo y ofrece un atajo:

* Click en la card → avanzar todos los ítems elegibles.
* Click en un ítem → avanzar solamente ese ítem.

Y esto también ayuda muchísimo con las modificaciones, porque una pizza que quedó en **Por preparar** todavía puede modificarse, mientras otra que ya está en **Horno** quizás ya no. El sistema deja de pensar en "el pedido está en horno" y empieza a pensar en "cada producto tiene su propio ciclo de vida". Esa diferencia es la que hace que el flujo de una pizzería sea mucho más flexible.


pero eso se relaciona con lo que veniamos hablando anteriormente

Sí, está directamente relacionado. De hecho, creo que acabás de encontrar la forma de resolver el problema de las modificaciones.

Antes decías:

> "El problema principal son las modificaciones."

Y el problema existía porque estabas pensando la comanda como una sola entidad con un único estado. Pero si permitís que **cada ítem tenga su propio estado**, las modificaciones pasan a ser mucho más manejables.

### Ejemplo

**Mesa 7**

* Pizza Muzzarella → 🔥 Horno
* Pizza Especial → 🟡 Por preparar
* Empanadas → 🟡 Por preparar

El cliente dice:

> "La Especial hacela mitad Roquefort."

Como la Pizza Especial sigue en **Por preparar**, la podés modificar directamente.

La Muzzarella no se toca porque ya está en horno.

---

### Otro caso

**Mesa 7**

* Pizza Muzzarella → 🔥 Horno
* Pizza Especial → 🔥 Horno
* Empanadas → 🟡 Por preparar

El cliente dice:

> "Agregame otra pizza."

No necesitás reenviar todo el pedido.

Simplemente se agrega:

* Nueva Pizza → 🟡 Por preparar

La card ahora queda:

* Pizza Muzzarella → 🔥 Horno
* Pizza Especial → 🔥 Horno
* Nueva Pizza → 🟡 Por preparar
* Empanadas → 🟡 Por preparar

---

### Entonces, ¿qué son las comandas amarillas?

Las comandas amarillas dejan de ser "el pedido modificado completo" y pasan a ser un indicador de:

> "Hubo cambios en algunos ítems del pedido."

Por ejemplo:

**Comanda original**

* Pizza Muzzarella
* Pizza Especial

**Comanda amarilla**

* ✏️ Pizza Especial → mitad Roquefort
* ➕ Nueva Pizza Muzzarella

La cocina sabe exactamente:

1. Qué ya está haciendo.
2. Qué todavía puede cambiar.
3. Qué se agregó.
4. Qué productos siguen pendientes.

---

### La relación entre ambas ideas

La posibilidad de tocar la **card completa** o un **ítem individual** es justamente lo que permite manejar las modificaciones sin romper el flujo.

* **Card completa:** acción masiva para avanzar todo el pedido.
* **Ítems individuales:** permiten estados mixtos.
* **Estados mixtos:** permiten modificaciones parciales.
* **Modificaciones parciales:** eliminan la necesidad de reenviar toda la comanda.

En otras palabras:

> **"Es individual pero en conjunto" significa que el pedido se visualiza como una sola comanda, pero el estado y las modificaciones se gestionan a nivel de cada producto. La card es un contenedor; los ítems son las verdaderas unidades de trabajo."**

Creo que esa frase resume todo lo que venían discutiendo desde el principio.


can you summarise the whole conversation in one system?

# Kitchen Order Management System (Pizzeria)

## Core Principle

A **Kitchen Order Card** represents a single table/order, but the **state and modifications are managed at the item level**.

> **The card is a container. The items are the actual units of work.**

This allows the kitchen to handle real-world scenarios where different products from the same order are at different stages of preparation.

---

# Data Model

## Order Card

Contains information shared by the entire order:

* Table number
* Order number
* Customer information (optional)
* Creation time
* General notes

The card itself should **not have one absolute status**, because its items may be in different states simultaneously.

---

## Order Items

Each item has its own independent lifecycle.

Examples:

**Table 7**

* Pizza Muzzarella → In Oven
* Pizza Especial → Preparing
* Empanadas → Delivered

This creates a **mixed-state order**, which accurately reflects how a pizzeria operates.

---

# Item States

Suggested states:

1. Pending / To Prepare
2. Preparing
3. Ready for Oven
4. In Oven
5. Ready for Delivery
6. Delivered
7. Cancelled

The exact workflow can be adjusted, but the important part is that **each item tracks its own state**.

---

# Card Actions

## Card Click

Acts as a bulk operation.

When the user clicks the entire card:

> Advance every eligible item to the next state.

Example:

Before:

* Pizza Muzzarella → Ready for Oven
* Pizza Especial → Ready for Oven
* Empanadas → Preparing

After clicking the card:

* Pizza Muzzarella → In Oven
* Pizza Especial → In Oven
* Empanadas → In Oven (if applicable)

This is the "move everything forward" action.

---

## Item Click

Acts only on selected items.

Example:

Before:

* Pizza Muzzarella → Ready for Oven
* Pizza Especial → Preparing
* Empanadas → Preparing

Clicking only the Muzzarella:

After:

* Pizza Muzzarella → In Oven
* Pizza Especial → Preparing
* Empanadas → Preparing

The card remains active because some items are still pending.

---

# Why Item-Level States Matter

A pizzeria frequently produces mixed orders.

Example:

**Table 12**

* Pizza #1 → In Oven
* Pizza #2 → Preparing
* Empanadas → Delivered

Treating the order as a single state would lose important information.

The kitchen needs to know exactly:

* What is already cooking
* What still needs work
* What has already been served
* What can still be modified

---

# Handling Modifications

The main challenge of the system is **order modifications**.

Examples:

* Add a new pizza
* Change toppings
* Cancel an item
* Convert a pizza to half-and-half
* Add notes to an existing item

---

# Modification Rules

Modifications depend on the item's current state.

### Items that can usually be modified

* Pending
* Preparing
* Ready for Oven

### Items that may be restricted

* In Oven
* Ready for Delivery

### Items that cannot be modified

* Delivered
* Cancelled

---

# Example

Initial order:

**Table 5**

* Pizza Muzzarella → Ready for Oven

Customer says:

> Make it half Roquefort.

Since the pizza has not entered the oven:

Update:

* Pizza ½ Muzzarella + ½ Roquefort → Ready for Oven

No new pizza is created.

The existing item is modified.

---

# Adding New Items

Initial:

**Table 5**

* Pizza Muzzarella → In Oven
* Pizza Especial → In Oven

Customer says:

> Add another Muzzarella.

Result:

* Pizza Muzzarella → In Oven
* Pizza Especial → In Oven
* Pizza Muzzarella → Pending

The new pizza is simply added as a new item.

Nothing else changes.

---

# Modification Cards (Yellow Tickets)

Yellow tickets should represent **deltas**, not full order reprints.

They indicate:

### Added

➕ Pizza Muzzarella

### Modified

✏️ Pizza Especial → Half Roquefort

### Cancelled

➖ Empanadas

Their purpose is:

> Inform the kitchen exactly what changed without forcing them to reinterpret the entire order.

---

# Fundamental Philosophy

```
Order Card
└── Item 1 → State A
└── Item 2 → State B
└── Item 3 → State C
└── Item 4 → State D
```

The card exists for organization and bulk actions.

The items own:

* Status
* Progress
* Modifications
* Preparation decisions

---

# Final System Definition

> A kitchen order is a container of independently managed order items. Each item progresses through its own preparation lifecycle and can be individually modified, advanced, or completed. The order card groups these items together and provides bulk operations, but it does not enforce a single status across the entire order. Modifications are represented as deltas (yellow tickets) that affect only the relevant items, allowing the kitchen to manage mixed-state orders accurately and efficiently.


there is only four states on the kds, are pendiente, horno, listo, entregado.

# Kitchen Display System (KDS) Workflow – Pizzeria

## Core Principle

An **Order Card** represents a table or order, but the **status is managed at the item level**.

> **The card is a container. The items are the units of work.**

This allows different products from the same order to be in different stages simultaneously.

---

# KDS States

There are only four states:

1. **Pendiente** (Pending)
2. **Horno** (In Oven)
3. **Listo** (Ready)
4. **Entregado** (Delivered)

Each item progresses independently:

```text
Pendiente → Horno → Listo → Entregado
```

---

# Order Structure

## Order Card

Contains shared information:

* Table number
* Order number
* Customer name (optional)
* Creation time
* General notes

The card itself does not have a single status because it can contain items in multiple states simultaneously.

Example:

**Table 7**

* Pizza Muzzarella → Horno
* Pizza Especial → Pendiente
* Empanadas → Entregado

The card is therefore in a **mixed state**.

---

# Item-Level Management

Each product has its own state.

Example:

**Table 12**

* Pizza #1 → Horno
* Pizza #2 → Pendiente
* Empanadas → Listo

This reflects how a pizzeria actually works:

* One pizza may already be cooking.
* Another may still be waiting to be assembled.
* Another may already be ready.

---

# Card Actions

## Clicking the Card

Acts as a bulk action.

> Move all eligible items to the next state.

Example:

Before:

* Pizza Muzzarella → Pendiente
* Pizza Especial → Pendiente
* Empanadas → Pendiente

After clicking the card:

* Pizza Muzzarella → Horno
* Pizza Especial → Horno
* Empanadas → Horno

---

## Clicking Individual Items

Acts only on selected products.

Example:

Before:

* Pizza Muzzarella → Pendiente
* Pizza Especial → Pendiente
* Empanadas → Pendiente

Clicking only the Muzzarella:

After:

* Pizza Muzzarella → Horno
* Pizza Especial → Pendiente
* Empanadas → Pendiente

The order remains active because there are still items pending.

---

# Modifications

The primary complexity of the system is **order modifications**.

Examples:

* Add a new pizza
* Change toppings
* Convert a pizza to half-and-half
* Cancel an item

---

# Modification Rules

Items can generally be modified while they are:

* **Pendiente**

Items in:

* **Horno**
* **Listo**
* **Entregado**

are progressively more restricted because production has already advanced.

---

# Example 1 – Modify Existing Pizza

Initial order:

**Table 5**

* Pizza Muzzarella → Pendiente

Customer says:

> Make it half Roquefort.

Result:

* Pizza ½ Muzzarella + ½ Roquefort → Pendiente

The same item is modified.

No new pizza is created.

---

# Example 2 – Add New Pizza

Initial:

**Table 5**

* Pizza Muzzarella → Horno
* Pizza Especial → Horno

Customer says:

> Add another Muzzarella.

Result:

* Pizza Muzzarella → Horno
* Pizza Especial → Horno
* Pizza Muzzarella → Pendiente

The new pizza starts at **Pendiente** while the others continue normally.

---

# Yellow Modification Cards

Yellow cards represent **changes to an existing order**, not a complete reprint.

They indicate:

**Added**
➕ Pizza Muzzarella

**Modified**
✏️ Pizza Especial → Half Roquefort

**Cancelled**
➖ Empanadas

Their purpose is:

> Show the kitchen exactly what changed while preserving the current state of every existing item.

---

# System Philosophy

```text
Order Card (Table 7)
├── Pizza Muzzarella → Horno
├── Pizza Especial → Pendiente
├── Empanadas → Listo
└── Fainá → Entregado
```

The card is used for grouping and bulk actions.

The items own:

* Their status
* Their progression through the KDS
* Their modifications
* Their readiness for preparation and delivery

---

# Final Definition

> A kitchen order is a container of independently managed order items. Each item moves through four states—Pendiente, Horno, Listo, and Entregado—and may be advanced individually or in bulk through the order card. Because items progress independently, an order can exist in a mixed state. Modifications are represented as yellow delta cards that communicate only the changes to the kitchen while preserving the state of all existing items.


if it is modified on the pos, it doesn't matter i should not restrict the orders.

I think that's actually an important design decision:

> **The KDS should never restrict modifications made from the POS. The POS is the source of truth.**

The KDS is only a visualization and workflow tool for the kitchen. It should not enforce business rules about whether an order can or cannot be changed.

# Principle

* **POS:** owns the order data.
* **KDS:** displays the current state of items and communicates changes to the kitchen.

If a waiter modifies an order in the POS:

* Add a pizza → KDS receives a new item in **Pendiente**.
* Change toppings → KDS receives an update for that item.
* Remove an item → KDS receives a cancellation/update event.
* Convert to half-and-half → KDS receives the modified item.

The KDS should not say:

> "You can't modify this because it's already in Horno."

That is ultimately a business decision for the restaurant staff.

---

# Why?

In a real pizzeria, people make exceptions all the time:

* "Take it out, we haven't put it in yet."
* "Add extra olives."
* "Make another one."
* "Actually, don't send that pizza."

The system should allow these situations instead of blocking them.

---

# Role of States

The four states:

```text
Pendiente → Horno → Listo → Entregado
```

describe **where an item is in the kitchen workflow**, not whether it can be edited.

States answer:

> "What is happening with this item right now?"

They do **not** answer:

> "Can the order still be changed?"

---

# Relationship with Yellow Modification Cards

Because modifications are always allowed from the POS, yellow cards become even more important.

They are simply:

> Delta events that inform the kitchen that something changed.

Examples:

**Table 7**

* ✏️ Pizza Muzzarella → Half Roquefort
* ➕ Add Fainá
* ➖ Remove Empanadas

The kitchen decides operationally what to do with those changes.

The KDS's responsibility is only to:

1. Keep item states (`Pendiente`, `Horno`, `Listo`, `Entregado`).
2. Display mixed-state orders correctly.
3. Show modifications clearly through yellow delta cards.
4. Never prevent updates coming from the POS.

---

# Final System Principle

> **The POS is the source of truth and may modify any order at any time. The KDS does not restrict modifications; it only tracks the workflow state of each item and communicates order changes to the kitchen through modification events (yellow cards).**


can you give me like the intention of the idea, because i need to explain to an AI the correct way, I mean i don't want the AI to make wrong decisions, I mean, i already have a structured system, but i want to modify it to include this philoshophy how can i explain that? 

You want to communicate the **philosophy and invariants**, not the implementation details. Otherwise, the AI will start inventing restrictions like "items in Horno cannot be modified."

I would explain it like this:

# KDS Design Philosophy

## Core Principle

The POS is the single source of truth for orders.

The Kitchen Display System (KDS) does not own order data and does not enforce business rules about whether an order can or cannot be modified. Any modification performed in the POS is considered valid and must be reflected in the KDS.

## Purpose of the KDS

The KDS exists to:

1. Visualize kitchen workflow.
2. Track the progression of each item through preparation states.
3. Communicate changes made to orders.
4. Allow kitchen staff to move items through the preparation process.

The KDS does not decide whether a modification is allowed. It only represents the current state of the order and informs the kitchen of changes.

## Item-Centric Model

An order card is a container of items.

The card itself is not the unit of work. The items are the units of work.

Each item has its own independent workflow state:

* Pendiente
* Horno
* Listo
* Entregado

Because items progress independently, a single order can contain items in multiple states simultaneously.

Example:

Table 7

* Pizza Muzzarella → Horno
* Pizza Especial → Pendiente
* Empanadas → Entregado

This is a valid state and should not be normalized into a single order status.

## Card vs Item Actions

The order card provides a convenience action for advancing multiple items at once.

Individual items may also be advanced independently.

Advancing an item does not require advancing the entire order.

## Modifications

Order modifications originate exclusively from the POS.

Examples:

* Add items
* Remove items
* Change toppings
* Convert pizzas to half-and-half
* Add notes

The KDS must always accept and display these modifications, regardless of the current workflow state of the affected items.

Workflow states represent preparation progress only. They never imply edit permissions or restrictions.

## Modification Communication

Modifications should be represented as change events (yellow cards or deltas).

The purpose of a modification event is to inform the kitchen:

* What changed
* Which item changed
* Whether items were added, modified, or removed

Modification events are informational. They do not alter the philosophy that the POS remains authoritative.

## Invariants

* POS is always authoritative.
* KDS never rejects POS changes.
* Items are the units of work.
* Cards are organizational containers and bulk-action mechanisms.
* Item states represent preparation progress only.
* An order may legitimately contain items in different states.
* Modification events communicate changes to the kitchen and are not permission checks.

The key sentence that will keep the AI from making incorrect decisions is probably this one:

> **Workflow states are descriptive, not restrictive. They describe where an item is in the kitchen process and must never be interpreted as permissions that prevent modifications coming from the POS.**

this is the current organisation.

Reading your current architecture, I wouldn't tell the AI to replace the system. I would tell it to reinterpret the ownership and meaning of the states.

Your current module already has most of the pieces:

pos.order → source order
pos.kitchen.ticket → order card
pos.kitchen.ticket.line → individual items
Line states already exist independently of ticket states
Delta tickets already exist (addition, cancellation, modification)

The philosophy you're adding is mostly a change in semantics and invariants, not a rewrite.

The Mental Model
Before (what the AI may incorrectly infer)
POS Order
    ↓
Kitchen Ticket
    ↓
Ticket State owns everything

This model leads to bad decisions:

"The ticket is in Horno, so modifications are forbidden."
"All lines must always share the same state."
"The order has one status."
After (the philosophy you want)
POS Order (source of truth)
        ↓
Kitchen Ticket (visual container)
        ↓
Kitchen Ticket Lines (units of work)
        ↓
Individual line states

The important change is:

The ticket does not own the order's business rules.
The ticket only organizes and visualizes items.

Ownership
POS owns
Products
Quantities
Notes
Additions
Removals
Modifications
KDS owns
Visual grouping
Workflow progression
Kitchen actions
Preparation progress
Nobody owns

"Whether the order may still be edited."

Because:

Modifications coming from the POS are always accepted.

Meaning of States

This is probably the most important thing to explain to the AI:

Pendiente
Horno
Listo
Entregado

These are not permissions.

They are observations.

They answer:

"Where is this item in the kitchen workflow?"

They do not answer:

"Can this item still change?"

Fundamental Invariant

I would literally put this in the prompt:

Workflow states are descriptive, not restrictive.

An item being in Pendiente, Horno, Listo, or Entregado does not determine whether the POS may modify it.

The POS is authoritative and may send changes at any time.

The KDS must always represent those changes.
Card Philosophy

Another invariant:

A kitchen ticket is not the unit of work.

A kitchen ticket is a container of work.

Kitchen ticket lines are the units of work.

Therefore:

Table 12
├── Pizza #1 → Horno
├── Pizza #2 → Pendiente
└── Empanadas → Entregado

This is a perfectly valid state.

The card itself is simply mixed.

It should never force all lines into the same state.

Card Click vs Item Click

This philosophy also explains your interaction model:

Card click
Advance every eligible line.

Convenience action only.

Item click
Advance only the selected line.

Primary workflow operation.

Because lines are independent.

Delta Philosophy

Your existing delta ticket system is actually very close to this philosophy.

I would redefine it as:

Delta tickets are communication events.

They do not replace existing tickets.
They do not redefine workflow states.
They only inform the kitchen that something changed.

Examples:

✏️ Modify Pizza Especial
➕ Add Pizza Muzzarella
➖ Remove Empanadas
The Philosophy I Would Give the AI
The POS is the source of truth.

The KDS is a projection of the POS optimized for kitchen operations.

A kitchen ticket is a visual container and not the authoritative representation of an order.

Kitchen ticket lines are the units of work and progress independently through the workflow states:
Pendiente → Horno → Listo → Entregado.

These states are descriptive only and represent preparation progress. They must never be interpreted as permissions or restrictions on order editing.

The POS may modify an order at any time. The KDS must always accept, synchronize, and display those modifications.

Delta tickets exist only to communicate changes to the kitchen. They are informational events and do not replace existing tickets or reset workflow state.

A single order may legitimately contain items in different states simultaneously. This mixed-state condition is expected and is a fundamental property of the system.

I think this is the piece that's currently missing from your document. The implementation already mostly supports it; you mainly need to make these invariants explicit so an AI doesn't accidentally
