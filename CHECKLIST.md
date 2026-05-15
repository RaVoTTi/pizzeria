# CHECKLIST — Pizzeria El Gordo (Technical IaC Reference)

## Architecture: Declarative Provisioning + Seed Data Pipeline

```
CSV/ + images/  ──→  addons/*.py (odoo shell)  ──→  Odoo DB (disposable)
        (source of truth)    (provisioning)          (derived state)
```

The database is **throwaway**. Nuclear reset destroys DB + volumes and rebuilds entirely from CSV files. Never edit Odoo directly via UI — everything must be reproducible from scratch.

---

## 1. Infrastructure Layer (how it runs)

| File | Purpose |
|------|---------|
| `docker-compose.yml` | 3 services: `nginx` (alpine), `web` (odoo:19.0 + cups-client), `db` (postgres:16) |
| `Dockerfile` | Extends `odoo:19.0`, adds `cups-client` for thermal printing |
| `config/odoo.conf` | `proxy_mode=True`, `workers=4`, admin password, addons paths |
| `config/nginx.conf` | Reverse proxy `elgordo.local:80` → `web:8069`, HTTPS stubs commented |
| `.env` | DB credentials + Mercado Pago tokens (gitignored) |
| `custom_addons/` | Third-party modules mounted at `/mnt/custom-addons` |

**Networks**: `frontend` (public, nginx+web), `backend` (internal, web+db).

**Volumes**: `odoo-web-data` (filestore), `odoo-db-data` (PG data).

---

## 2. Data Layer (source of truth — CSV files)

| CSV File | Lines | What |
|----------|-------|------|
| `csv/categories.csv` | 11 | Hierarchical product categories |
| `csv/products.csv` | ~78 | All ingredients, pizzas, drinks, empanadas, delivery fee |
| `csv/producto_masa.csv` | 1 | "Bollo de Masa" intermediate product |
| `csv/pizzas.csv` | N | Pizza products (Mostrador variants) |
| `csv/pizzas_salon.csv` | N | "[S] Salon" pizza variants (higher price) |
| `csv/mitades.csv` | N | Half-&-half products |
| `csv/mitades_salon.csv` | N | "[S] Salon" half-&-half variants |
| `csv/empanadas.csv` | N | Empanada products |
| `csv/empanadas_salon.csv` | N | "[S] Salon" empanada variants |
| `csv/unidades.csv` | ~2 | Custom UoM: "Pinta" (~0.473L) |
| `csv/receta_del_bollo.csv` | 3 | Bollo recipe: harina + agua + levadura |
| `csv/receta_pizzas_con_masa.csv` | 82 | All pizza phantom BoMs (ingredients per pizza) |
| `csv/employees.csv` | N | Employee definitions (for POS PIN login) |
| `csv/precios_salon.csv` | N | Salon price adjustments/surcharges |
| `images/layout*.png` | ~5 | Floor plan backgrounds |
| `images/productos/` | ~N | Product images named by product ID |

### CSV Dependency Graph (import order matters)

```
unidades.csv ──→ categories.csv ──→ products.csv + producto_masa.csv
                                           │
                                           ▼
                              receta_del_bollo.csv
                              receta_pizzas_con_masa.csv
                                           │
                                           ▼
                              pizzas_salon.csv / mitades_salon.csv / empanadas_salon.csv
                                           │
                                           ▼
                              precios_salon.csv (channel pricing)
```

### CSV Field Conventions

- `id` column = external identifier (used as `default_code` in Odoo)
- `categ_id/id` = references category by its CSV `id` column
- `uom_name` = UoM name string (mapped via `import_lib.py:UOM_SEARCH`)
- `standard_price` = cost price (ingredients only)
- `list_price` = sale price (0 for non-saleable items)
- `image_1920` = filename in `images/productos/` or full path
- `detailed_type` = `product` (storable, inventory-tracked) or `consu` (consumable)
- Salon variants prefixed with `[S]` in name

---

## 3. Provisions Layer (scripts that read CSV → Odoo)

### Import Sequence (`scripts/import-data.sh` — 12 steps)

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `import_initial.py` | Installs modules (`stock`, `mrp`, `point_of_sale`, `pos_restaurant`) + custom UoMs |
| 2 | `import_01_categories.py` | Creates product categories from `categories.csv` |
| 3 | `import_02_ingredients.py` | Creates raw ingredients + Bollo de Masa + drinks + delivery fee product |
| 4 | `import_03_products.py` | Creates saleable products (pizzas, mitades, empanadas) from CSVs |
| 5 | `import_04_boms.py` | Creates phantom BoMs from recipe CSVs + Salon BoMs (copied from Mostrador) |
| 6 | `import_05_pos.py` | Creates POS categories, assigns products, configures POS |
| 7 | `setup_floors.py` | Restaurant floor plan with 18 tables across 2 floors |
| 8 | `set_language_spanish.py` | Switches Odoo UI language to Spanish |
| 9 | `remove_taxes.py` | Removes all taxes from products, creates Cubierto (10% table fee) |
| 10 | `setup_test_inventory.py` | Sets initial stock quantities for all ingredients |
| 11 | `setup_mercado_pago.py` | Configures Mercado Pago payment terminal |
| 12 | `setup_kitchen_display.py` | Configures Kitchen Display System |
| — | `validate_boms.py` (post-run) | Validates all phantom BoMs, checks for double-deduction bugs |
| — | `setup_channel_pricing.py` (bonus) | Configures 3 pricelists: Salon / Mostrador / Delivery |

### Operational Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `nuclear-reset.sh` | Full rebuild: `docker compose down -v`, reinstall modules, reimport all data |
| `clean-data.sh` | Wipe DB data only (preserves Docker volumes, runs import) |
| `import-data.sh` | 12-step import pipeline (no Docker teardown) |
| `backup.sh` | pg_dump with 7-day retention |
| `restore.sh` | DB restore with confirmation prompt |
| `odoo-shell.sh` | Helper to run ad-hoc odoo shell commands |
| `setup-printer.sh` | CUPS printer setup (mounts cups.sock, tests print) |
| `generate-test-order.sh` | Creates a test POS order + verifies kitchen ticket |
| `reload-kitchen-addon.sh` | Rebuilds image + upgrades kitchen module + restarts web |
| `run-tests.sh` | Test runner: unit/shell/e2e/kitchen/lint |

### Diagnostic Scripts (`scripts/diag/`)

| Script | Purpose |
|--------|---------|
| `check_bollo.py` | Verify Bollo de Masa product + BoM exist correctly |
| `check_product_types.py` | Diagnostic: check product type/storable flags |
| `diagnose_floors.py` | Check floor plan configuration |
| `fix_floors.py` | Repair floor plan issues |
| `fix_bollo_harina.py` | Fix Bollo Harina product reference |
| `fix_product_types.py` | Fix product type flags |
| `extract_coordinates.py` | Extract table coordinates from floor layout |
| `upload_pizza_images.py` | Upload product images from `images/productos/` |

---

## 4. Testing

### Test Types

| Type | Command | What |
|------|---------|------|
| Odoo TransactionCase | `scripts/run-tests.sh unit` | Unit tests via `--test-tags` |
| Odoo Shell integration | `scripts/run-tests.sh shell` | Runs `tests/test_*.py` via odoo shell |
| Playwright E2E | `scripts/run-tests.sh e2e` | Browser tests from `e2e/specs/` |
| Kitchen-specific | `scripts/run-tests.sh kitchen` | Kitchen ticket workflow tests |

### Test Files

| File | What it tests |
|------|---------------|
| `tests/test_kitchen_workflow.py` | Kitchen ticket creation, formatting, printing |
| `tests/test_kitchen_failure_modes.py` | Error handling: no printer, missing product, etc. |
| `tests/test_pos_inventory_deduction.py` | Phantom BoM stock deduction via POS order |
| `tests/test_phantom_odoo19.py` | BoM chain validation + Odoo 19 is_storable check |
| `e2e/specs/` | KDS model tests, login smoke test, advance KDS tests |

---

## 5. Critical Concepts for Correctness

### Phantom BoM Chain (THE critical feature)

```
Flour + Water + Yeast ──→ Bollo de Masa (phantom, no produce step)
                                │
                                ▼
Bollo + Cheese + Sauce + Toppings ──→ Pizza (phantom, no produce step)
```

- Both levels use `type='phantom'` — Odoo auto-deducts ingredients on POS sale
- **No manufacturing orders needed** — essential for fast restaurant workflow
- **Two-level** = change dough recipe once, all pizzas update
- Each pizza sale = 6+ stock moves (flour, water, yeast, sauce, cheese, topping × qty)

### Salon [S] Products Pattern

Every Mostrador (counter) product has a corresponding `[S] Salon` variant:
- **Mostrador**: base price, takeaway/pickup channel
- **[S] Salon**: higher price (dine-in surcharge), dining room channel
- BoMs: [S] Salon variants **copy** the Mostrador recipe (same ingredients, NOT linked via product — avoids double deduction)
- POS categories: `[S]` variants shown in separate `[S] Pizzas`, `[S] Mitades`, `[S] Empanadas` categories

### Channel Pricing (3 Pricelists)

| Pricelist | What | Applied to |
|-----------|------|------------|
| Salon | Dine-in prices (Mostrador + surcharge) | [S] Salon products |
| Mostrador | Base counter prices | Non-[S] products |
| Delivery | Takeaway prices | Non-[S] products + $1500 delivery fee |

### Product Type Rules (Odoo 19)

- `detailed_type='product'` → `is_storable=True` → phantom BoM works ✓
- `detailed_type='consu'` → `is_storable=False` → phantom BoM will NOT deduct stock
- In Odoo 19, `is_storable` is computed (not directly settable). Set via `type` field or `is_storable` on creation.
- Ingredients MUST be storable for phantom BoM deduction to work
- Service products (delivery fee) have their own handling

---

## 6. Hard Rules (For LLM Contributors)

### ✅ Allowed
- Edit CSV files (source of truth)
- Create/edit `addons/*.py` provisioning scripts (use `import_lib.py` helpers)
- Create new files in `custom_addons/` (Odoo modules with `__manifest__.py`)
- Use `env['model'].search/create/write` via odoo shell
- Use `import_lib.py` helpers: `csv_rows()`, `get_uom_id()`, `get_categ_id()`, `create_product_from_csv()`, `load_product_index()`, `load_category_index()`
- Run `nuclear-reset.sh --skip-docker` to reimport after CSV changes

### ❌ Forbidden
- **No raw SQL** — never use `env.cr.execute()` or direct SQL
- **No UI configuration** — every change must be scripted
- **No modifying Odoo core** — never change files inside Odoo modules; only use `addons/` or `custom_addons/`
- **No direct DB editing** — never use psql/pgadmin to change data
- **No hardcoded IDs** — always search by name or use `default_code`
- **No skipping the pipeline** — if CSV changes, re-run import. Don't patch DB directly.

### General Principles

1. **Reproducibility**: Every change must survive `nuclear-reset.sh`
2. **Idempotency**: Import scripts check `search()` before `create()`
3. **No silent failures**: Log warnings for missing products/uoms/categories
4. **Test after provision**: Run `validate_boms.py` to verify BoM integrity
5. **Commit CSV + script, not DB state**: The repo contains the recipe, not the cooked meal

---

## 7. File Inventory (all non-obvious files)

| File | Notes |
|------|-------|
| `addons/import_lib.py` | Shared library: CSV reader, UoM/category lookup, image encoder, product creator |
| `addons/import_products.py.bak` | Old monolithic import (replaced by step-by-step pipeline) |
| `addons/diag_salon_double.py` | Diagnostic for double-deduction bugs in Salon BoMs |
| `addons/clean_data.py` | DB cleanup (called by `clean-data.sh`) |
| `csv/precios_salon.csv` | Price overrides for Salon channel |
| `csv/summary.md` | Auto-generated product counts |
| `csv/explanation.md` | CSV relationship diagram |
| `csv/employees.csv` | Employee records (PIN, roles) |
| `images/layout.xcf` | GIMP source file for floor plan |
| `scripts/scripts-ideas.md` | Brain-dump of emergency/recovery script ideas |
| `e2e/test-results/` | Test artifacts (gitignored) |
| `.env` | Created from `.env.example` pattern (gitignored, not in repo) |

---

## 8. Common Tasks (Quick Reference)

### Add a new pizza product

1. Add entry to `csv/products.csv` and `csv/pizzas.csv`
2. Add recipe to `csv/receta_pizzas_con_masa.csv`
3. Add image to `images/productos/PIZZAXX.png` if desired
4. Run `scripts/import-data.sh` (or `nuclear-reset.sh --skip-docker`)

### Change ingredient cost

1. Edit `standard_price` column in `csv/products.csv`
2. Re-run step 3 only: `docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_02_ingredients.py`
3. Or full reimport

### Modify dough recipe (affects all pizzas)

1. Edit `csv/receta_del_bollo.csv` (flour/water/yeast quantities)
2. Run step 5 of import: `docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_04_boms.py`
3. Validate: `docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/validate_boms.py`

### Debug a failed import

1. Check the Python traceback in the odoo shell output
2. Common issues: missing parent category, UoM not found, CSV column name mismatch
3. Run `nuclear-reset.sh --skip-docker` for a clean retry

### Run tests

```bash
scripts/run-tests.sh lint     # Python lint on custom_addons/
scripts/run-tests.sh unit     # Odoo TransactionCase tests
scripts/run-tests.sh shell    # Integration tests via odoo shell
scripts/run-tests.sh e2e      # Playwright browser tests
```

---

## 9. Implementation Status (phases tracking)

### Phase 0 — Architecture Foundation ✅ (9/9 done)
### Phase 1 — Core Operations ⚠️ (18/20 done)
- ❌ Warehouse/stock location config in import
- ❌ POS payment methods configuration (cash + MP)

### Phase 2 — Employees & Roles ❌ (0/5)
### Phase 3 — Hardware & Network ⚠️ (4/8)
### Phase 4 — Backup & Reliability ⚠️ (4/8)
### Phase 5 — Security ⚠️ (3/8)
### Phase 6 — Customization & Reporting ❌ (0/5)
### Phase 7 — E-commerce & Scaling ❌ (0/3)
### Phase 8 — Printer & Kitchen Display ❌ (0/6)
### Phase 9 — Emergency & Recovery Scripts ❌ (0/9)
### Phase 10 — Performance & Maintenance ❌ (0/7)
### Phase 11 — AI-Suggested Improvements ❌ (0/8)

**Total**: 38/96 done, 4 partial, 54 not done.

---

## 10. Key Odoo Model References

| Model | Used for |
|-------|----------|
| `product.template` | Products (ingredients, pizzas, drinks, etc.) |
| `product.product` | Product variants (1:1 with template in this project) |
| `product.category` | Product categories (hierarchical tree) |
| `uom.uom` | Units of measure (kg, L, Units, Pinta) |
| `mrp.bom` | Bill of Materials (all `type='phantom'`) |
| `pos.category` | POS-specific categories (separate from product categories) |
| `pos.config` | POS configuration (name, available categories, pricelist) |
| `pos.session` | POS session management |
| `pos.order` | POS orders (sale transactions) |
| `pos.payment.method` | Payment methods (Cash, Mercado Pago) |
| `restaurant.table` | Floor plan tables (18 tables, 2 floors) |
| `restaurant.floor` | Floor definitions |
| `product.pricelist` | Channel pricing: Salon/Mostrador/Delivery |
| `product.pricelist.item` | Per-product price surcharges (Cubierto 10%) |
| `pos.kitchen.ticket` | Kitchen display tickets (from custom module) |
| `stock.location` | Warehouse / stock locations |
| `stock.quant` | Current stock quantities |
| `stock.move` | Stock moves (generated by phantom BoM explosion on sale) |
| `res.partner` | Customers |
| `res.users` | User accounts (not yet configured) |
| `hr.employee` | Employee records (not yet configured) |
