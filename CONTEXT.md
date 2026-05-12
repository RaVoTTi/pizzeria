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
├── addons/                      # Import & setup scripts (run via odoo shell)
│   ├── import_initial.py        # Installs base modules + UoMs
│   ├── import_01_categories.py  # Product categories
│   ├── import_02_ingredients.py # Raw ingredients + Bollo de Masa
│   ├── import_03_products.py    # Saleable products (pizzas, empanadas, mitades)
│   ├── import_04_boms.py        # Phantom BoMs
│   ├── import_05_pos.py         # POS categories & config
│   ├── import_lib.py            # Shared library (CSV reader, helpers)
│   ├── setup_floors.py          # Restaurant floor plan (18 tables)
│   ├── setup_kitchen_display.py # Kitchen screen configuration
│   ├── setup_mercado_pago.py    # Mercado Pago payment terminal
│   ├── setup_test_inventory.py  # Initial stock quantities
│   ├── set_language_spanish.py  # Language switch to Spanish
│   ├── remove_taxes.py          # Tax removal from products
│   └── validate_boms.py         # BoM diagnostic/validation
├── config/
│   ├── nginx.conf               # Reverse proxy config (HTTP, HTTPS stubs ready)
│   └── odoo.conf                # Odoo config (db, proxy, workers, addons_path)
├── custom_addons/               # Third-party/custom Odoo modules
│   └── pos_kitchen_screen_odoo/ # POS Kitchen Screen (Cybrosys, v18.0.1.2.0)
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
│   ├── nuclear-reset.sh         # Full teardown + fresh init + data import
│   ├── clean-data.sh            # Wipe DB data only (preserve Docker)
│   ├── import-data.sh           # 12-step data import pipeline
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

## Custom Addons

Custom Odoo modules live in `custom_addons/`. Each subdirectory is a standalone
module (must contain `__manifest__.py` at its root). The directory is mounted
into the Docker container at `/mnt/custom-addons` and included in `addons_path`
in `config/odoo.conf`.

To add a new custom module:
1. Place the module folder directly inside `custom_addons/` (no extra nesting).
2. Run `scripts/nuclear-reset.sh --skip-docker` to reinstall modules and reimport data.
   Or add the module name to `nuclear-reset.sh`'s `-i` list for full resets.

## Data Import Pipeline

The `import-data.sh` script runs 12 sequential odoo shell invocations:

1. `import_initial.py` — Installs required modules + custom UoMs
2. `import_01_categories.py` — Product categories from `categories.csv`
3. `import_02_ingredients.py` — Raw ingredients + Bollo de Masa intermediate product
4. `import_03_products.py` — Saleable products (pizzas, mitades, empanadas)
5. `import_04_boms.py` — Phantom BoMs from `receta_del_bollo.csv` + `receta_pizzas_con_masa.csv`
6. `import_05_pos.py` — POS categories & config
7. `setup_floors.py` — Restaurant floor plan (18 tables)
8. `set_language_spanish.py` — Language switch to Spanish
9. `remove_taxes.py` — Tax removal from all products
10. `setup_test_inventory.py` — Initial stock quantities
11. `setup_mercado_pago.py` — Mercado Pago payment terminal setup
12. `setup_kitchen_display.py` — Kitchen Display System (KDS) configuration

Closes with `validate_boms.py` diagnostic and a container restart.

## Access

- **URL:** `http://elgordo.local` (or `http://192.168.1.100`)
- **Database:** `elgordo`
- **Odoo admin password:** stored in `config/odoo.conf` (`admin_passwd`)
- **DB credentials:** stored in `.env` (gitignored)

## Modules in Use

- `stock` — Inventory management
- `mrp` — Manufacturing / BoMs (phantom type)
- `point_of_sale` — POS interface for tablets
- `pos_restaurant` — Table management, floor plans
- `pos_preparation_display` — Order preparation display
- `pos_kitchen_screen_odoo` — Kitchen screen (Cybrosys, loaded from `custom_addons/`)

## Threats / Risks (from docs)

- Theoretical vs. actual stock drift → requires weekly **Physical Inventory** adjustments
- No offline POS fallback if server dies → **Paper Fallback** plan documented
- No automated offsite backups → backup script exists but no cloud push
- No role-based access yet → all users would have admin access