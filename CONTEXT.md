# Project Context — Pizzeria El Gordo

## Overview

An Odoo 19-based ERP system for **Pizzeria El Gordo**, designed to manage pizza sales, inventory tracking of raw ingredients, and point-of-sale operations. The entire stack runs locally on Docker, behind an Nginx reverse proxy, with offline-first design for restaurant reliability.

## Architecture

```
Tablet (POS) ──→ Nginx (:80) ──→ Odoo (:8069) ──→ PostgreSQL (:5432)
                                [elgordo.local]
```

- **Odoo 19** — Main application (Community Edition)
- **PostgreSQL 16** — Isolated database container
- **Nginx (Alpine)** — Reverse proxy, future HTTPS-ready
- **Docker Compose** — Orchestration with two networks (`frontend`, `backend`)

## Directory Structure

```
odoo-pizzeria/
├── addons/
│   └── import_pizzas.py        # Data import script (categories, products, BoMs, POS config)
├── config/
│   ├── nginx.conf              # Reverse proxy config (HTTP, HTTPS stubs ready)
│   └── odoo.conf               # Odoo config (db, proxy, workers)
├── csv/
│   ├── categories.csv           # 11 product categories (hierarchical tree)
│   ├── products.csv             # 78 products (ingredients, pizzas, drinks, empanadas)
│   ├── producto_masa.csv        # 1 intermediate product: "Bollo de Masa" (pre-pizza dough)
│   ├── receta_del_bollo.csv     # 3 lines: dough recipe (flour + water + yeast)
│   ├── receta_pizzas_con_masa.csv # 82 lines: all pizza BoMs (phantom/kit type)
│   ├── unidades.csv             # Custom UoM: "Pinta" (beer glass, ~0.473L)
│   ├── unidades-smaller.csv     # Alternative/smaller UoM definitions (unused)
│   ├── recipes.csv              # Empty (unused)
│   └── explanation.md           # CSV relationship diagram
├── docs/
│   ├── plan.md                  # Complete production-ready plan (5 phases)
│   ├── history.md               # Full phased plan (7 phases) with refinements
│   └── network-setup.md         # Hardware, static IPs, DNS, Ubuntu setup
├── scripts/
│   ├── backup.sh                # Nightly pg_dump with 7-day retention
│   ├── restore.sh               # Database restore with confirmation prompt
│   └── odoo-shell.sh            # Odoo shell helper
├── docker-compose.yml           # 3-service stack (nginx, web, db)
├── .env                         # DB credentials (gitignored)
├── .gitignore
└── HOW_TO_USE.md                # Quick-start and import instructions
```

## Key Design Decisions

### Phantom/Kit BoMs (Critical)

Pizzas use **phantom BoMs** — when a pizza is sold via POS, Odoo automatically deducts raw ingredients (flour, cheese, sauce) without requiring the kitchen to process manufacturing orders. This is essential for a fast-paced restaurant where cooks cannot click "Produce" per order.

### Two-Level BoM Chain

```
Flour + Water + Yeast ──→ Bollo de Masa (phantom BoM)
                                    │
                                    ▼
Bollo + Cheese + Sauce + Toppings ──→ Pizza (phantom BoM)
```

The "Bollo de Masa" is an intermediate product with its own recipe. All pizza BoMs reference it, so changing the dough recipe updates all pizzas at once.

### Offline-First

The system is designed to run entirely on a local network. Tablets connect to `elgordo.local` via Nginx. No cloud dependency. UPS required for server + router + printer.

### Product Categories

```
Todos (All)
├── GASTOS OPERATIVOS
│   └── Servicios (Luz/Gas)
├── INSUMOS
│   ├── Materia Prima Cocina
│   ├── Barriles Y Gas
│   └── Bebidas Sin Alcohol
└── VENTAS
    ├── Pizzas
    ├── Cerveza Barra
    └── Deliveries
```

## Data Import Pipeline

The `import_pizzas.py` script runs inside the Odoo shell and:

1. Installs required modules (`stock`, `mrp`, `point_of_sale`)
2. Creates custom UoM ("Pinta")
3. Creates product categories from `categories.csv`
4. Creates products from `products.csv` + `producto_masa.csv`
5. Creates phantom BoMs from `receta_del_bollo.csv` + `receta_pizzas_con_masa.csv`
6. Updates POS config name to "Pizzeria El Gordo"

## Access

- **URL:** `http://elgordo.local` (or `http://192.168.1.100`)
- **Database:** `elgordo`
- **Odoo admin password:** stored in `config/odoo.conf` (`admin_passwd`)
- **DB credentials:** stored in `.env` (gitignored)

## Modules in Use

- `stock` — Inventory management
- `mrp` — Manufacturing / BoMs (phantom type)
- `point_of_sale` — POS interface for tablets

## Threats / Risks (from docs)

- Theoretical vs. actual stock drift → requires weekly **Physical Inventory** adjustments
- No offline POS fallback if server dies → **Paper Fallback** plan documented
- No automated offsite backups → backup script exists but no cloud push
- No role-based access yet → all users would have admin access