# Implementation Checklist — Pizzeria El Gordo

Based on the plans in `docs/plan.md`, `docs/history.md`, and `docs/network-setup.md`.
Cross-referenced against actual files in the repository.

---

## Phase 0 — Architecture Foundation

> From: `docs/history.md` Phase 0, `docs/plan.md` Phase 2

| Item | Status | Notes |
|------|--------|-------|
| Docker Compose with 3 services (nginx, odoo, postgres) | ✅ Done | `docker-compose.yml` — odoo:19, postgres:16, nginx:alpine |
| PostgreSQL in separate container | ✅ Done | `db` service on internal `backend` network |
| Named volumes for persistence | ✅ Done | `odoo-web-data`, `odoo-db-data` |
| Nginx reverse proxy (HTTP) | ✅ Done | `config/nginx.conf` — listens :80, proxies to `web:8069` |
| Nginx HTTPS ready (stubs) | ✅ Done | Commented blocks for SSL and HTTP→HTTPS redirect in `nginx.conf` |
| Odoo config with proxy mode | ✅ Done | `config/odoo.conf` — `proxy_mode = True`, 4 workers |
| `.env` for secrets | ✅ Done | Gitignored, referenced in `docker-compose.yml` |
| `.gitignore` | ✅ Done | Excludes `.env`, `backups/`, `__pycache__/`, etc. |
| Two Docker networks (frontend/backend) | ✅ Done | `backend` is `internal: true`, `frontend` is public |

## Phase 1 — Core Operations (Inventory & BoMs)

> From: `docs/history.md` Phase 1, `docs/plan.md` Phase 3

| Item | Status | Notes |
|------|--------|-------|
| Product categories (11, hierarchical) | ✅ Done | `csv/categories.csv` — tree: Todos → Gastos/Insumos/Ventas |
| Products (78+ ingredients/pizzas/drinks) | ✅ Done | `csv/products.csv` + `csv/producto_masa.csv` |
| Custom UoM "Pinta" (~0.473L) | ✅ Done | `csv/unidades.csv`, created in import script |
| Phantom/Kit BoMs for pizzas | ✅ Done | `csv/receta_pizzas_con_masa.csv` — 82 lines |
| Two-level BoM chain (Bollo intermediate) | ✅ Done | `csv/receta_del_bollo.csv` → Bollo de Masa → pizzas |
| Import script (categories, products, BoMs, POS) | ✅ Done | `addons/import_products.py` — 6-step pipeline via `nuclear-reset.sh` |
| POS config name updated | ✅ Done | Sets name to "Pizzeria El Gordo" |
| Restaurant floor plans & tables | ✅ Done | `addons/setup_floors.py` — 18 tables across 2 floors |
| Spanish language | ✅ Done | `addons/set_language_spanish.py` |
| Taxes removed from products | ✅ Done | `addons/remove_taxes.py` |
| Initial stock loaded | ✅ Done | `addons/setup_test_inventory.py` |
| Nuclear reset script (full rebuild) | ✅ Done | `scripts/nuclear-reset.sh` — 7-step automated rebuild from scratch |
| Modules auto-installed (stock, mrp, point_of_sale, pos_restaurant) | ✅ Done | `nuclear-reset.sh` installs them; `pos_restaurant` added |
| Cost prices on ingredients | ✅ Done | `products.csv` includes `standard_price` per product |
| Sale prices on salable products | ✅ Done | `products.csv` includes `list_price`; `sale_ok` auto-set |
| Products available in POS | ✅ Done | `available_in_pos` set when `list_price > 0` and not service |
| Warehouse/location setup | ❌ Not done | No default warehouse or stock location config in import |
| POS payment methods | ❌ Not done | No payment method configuration in import script |
| POS fiscal position/taxes | ❌ Not done | No tax or fiscal position setup |

## Phase 2 — Employees & Roles

> From: `docs/history.md` Phase 2, `docs/plan.md` Phase 4

| Item | Status | Notes |
|------|--------|-------|
| Manager user with full access | ❌ Not done | No user creation in code; default admin only |
| Cashier user with POS-only access | ❌ Not done | No role/permission definitions |
| Kitchen user with inventory-only access | ❌ Not done | No role/permission definitions |
| 4-digit PIN login for POS | ❌ Not done | No POS user barcodes/PINs configured |
| Employee tracking (basic) | ❌ Not done | No HR module or employee records |

## Phase 3 — Hardware & Network

> From: `docs/plan.md` Phase 1, `docs/network-setup.md`

| Item | Status | Notes |
|------|--------|-------|
| Hardware checklist documented | ✅ Done | `docs/network-setup.md` — Mini PC, tablets, printer, UPS |
| Static IP assignments documented | ✅ Done | Server: 192.168.1.100, Printer: 192.168.1.200 |
| Local DNS config documented | ✅ Done | Three options: router DNS, tablet hosts file, dnsmasq |
| Ubuntu Server setup guide | ✅ Done | `docs/network-setup.md` — commands for Docker install |
| Nginx `server_name` includes `elgordo.local` | ✅ Done | `config/nginx.conf` — `server_name elgordo.local 192.168.1.100` |
| Thermal printer configuration | ❌ Not done | ESC/POS printer setup needed for tickets/receipts |
| Kitchen Display System (KDS) | ❌ Not done | `pos_restaurant` module installed; KDS screen configuration needed |
| Hardware actually procured | ❌ Not done | Physical hardware — outside code scope |

## Phase 4 — Backup & Reliability

> From: `docs/plan.md` Phase 5, `docs/history.md` Phase 6

| Item | Status | Notes |
|------|--------|-------|
| Backup script (pg_dump + 7-day retention) | ✅ Done | `scripts/backup.sh` |
| Restore script (with confirmation prompt) | ✅ Done | `scripts/restore.sh` |
| Odoo shell helper | ✅ Done | `scripts/odoo-shell.sh` |
| Nuclear reset script | ✅ Done | `scripts/nuclear-reset.sh` — full rebuild in ~3 min |
| Cron job for nightly backups | ⚠️ Partial | Documented in `docs/network-setup.md` but no crontab/cron Docker setup |
| Offsite/cloud backup push | ❌ Not done | Script only saves locally; no S3/B2/rclone integration |
| Odoo filestore backup | ❌ Not done | Only DB dump; `odoo-web-data` volume not backed up |
| Update/migration strategy (clone → test → deploy) | ❌ Not done | Documented in plan but no scripts or procedure file |

## Phase 5 — Security

> From: `docs/history.md` Phases 0 & 5, `docs/plan.md` Phase 2

| Item | Status | Notes |
|------|--------|-------|
| Non-default admin password | ✅ Done | `config/odoo.conf` — `admin_passwd = 9vyf-dcwb-bmp6` |
| Non-default DB credentials | ✅ Done | `.env` file with custom credentials |
| Backend network isolated | ✅ Done | `backend` network is `internal: true` in compose |
| Strong DB user (not `postgres` superuser) | ⚠️ Partial | Uses `odoo` user but `POSTGRES_DB=postgres` in `.env` reference |
| Role-based access control | ❌ Not done | Same as Phase 2 roles — no user segregation |
| Fail2Ban | ❌ Not done | Not mentioned in compose or config |
| VPN / Tailscale | ❌ Not done | Documented as future phase only |
| HTTPS / SSL | ❌ Not done | Stub config exists but no certs or enforcement |

## Phase 6 — Customization & Reporting

> From: `docs/history.md` Phase 3

| Item | Status | Notes |
|------|--------|-------|
| Custom modules in `/addons` | ⚠️ Partial | Only `import_pizzas.py` (data script, not an Odoo module) |
| "Most sold pizza" report | ❌ Not done | Not implemented |
| "Ingredient consumption per day" report | ❌ Not done | Not implemented |
| Cost/margin per pizza dashboard | ❌ Not done | Odoo can compute this from cost prices, but no custom view |
| Stock adjustment workflow automation | ❌ Not done | Manual Physical Inventory — no reminder or scheduling |

## Phase 7 — E-commerce & Scaling

> From: `docs/history.md` Phases 4 & 7

| Item | Status | Notes |
|------|--------|-------|
| eCommerce module | ❌ Not done | Future phase; not installed or configured |
| Multi-location support | ❌ Not done | Future phase |
| Multiple POS terminals | ❌ Not done | Only one POS config defined |

## Phase 8 — Printer & Kitchen Display

> Hardware output: receipt printers and kitchen screens for order flow.

| Item | Status | Notes |
|------|--------|-------|
| ESC/POS thermal printer driver setup | ❌ Not done | Need IoT box or direct USB/Network printer in Docker |
| Receipt printer mapping in POS config | ❌ Not done | Configure receipt + order printer in Odoo POS settings |
| Kitchen Display System (KDS) screen | ❌ Not done | POS Kitchen module for real-time order display on kitchen monitor |
| Printer self-test / connectivity verification | ❌ Not done | Script or procedure to confirm printer is reachable |
| Kitchen order ticket formatting | ❌ Not done | Customize ticket layout (pizza name, toppings, table number) |
| Auto-print on order confirmation | ❌ Not done | Kitchen ticket prints automatically when POS order is sent |

## Phase 9 — Emergency & Recovery Scripts

> From: `scripts/scripts-ideas.md` — "restaurant battlefield recovery tooling"
> Philosophy: **optimize for continuity of service**. Keep the kitchen alive, keep waiters selling, recover later.

| Item | Status | Notes |
|------|--------|-------|
| `kitchen_panic.sh` — restart web, clear printer queues, reprint last 10 min orders | ❌ Not done | Highest value: kitchen tickets are critical during rush |
| `ghostbuster.sh` — purge stale draft orders, release stuck tables | ❌ Not done | Targets `pos.order` draft state, older than X hours, no payments |
| `tablet_resync.sh` — invalidate POS cache, rebuild session for cursed tablet | ❌ Not done | Single-tablet recovery without full reset |
| `safe_mode.sh` — disable accounting/stock validation during rush hour | ❌ Not done | Turns Odoo into "just a cash register" for emergencies |
| `time_machine_reset.sh` — export today's sales, nuclear reset, re-import revenue | ❌ Not done | Preserves Friday income while clearing corruption |
| `service_kick.sh` — restart only web container (5s downtime) | ⚠️ Partial | `docker compose restart web` exists but no dedicated script |
| `freeze_state.sh` — snapshot DB, logs, active orders before risky operations | ❌ Not done | Creates a "crash snapshot" before emergency surgery |
| `force_stock.sh` — emergency inventory override for "out of stock" blocks | ❌ Not done | Bulk inventory adjustment, not raw `qty_available` override |
| `blackout_mode.sh` — disable external integrations, local-only operation | ❌ Not done | For when internet/external services are down |

## Phase 10 — Performance & Maintenance

> From: `scripts/scripts-ideas.md` — operational compression and DB health
> Stock move explosion from phantom BoMs (6+ moves per pizza × 300 pizzas/night = thousands of rows).

| Item | Status | Notes |
|------|--------|-------|
| `compress_stock_moves.sh` — aggregate old ingredient consumptions to daily totals | ❌ Not done | Reduces DB bloat from phantom BoM explosions |
| `archive_pos_orders.sh` — move old orders to archive/export | ❌ Not done | Export detail to JSON/CSV, keep totals in Odoo |
| `vacuum_friday.sh` — PostgreSQL VACUUM ANALYZE before rush | ❌ Not done | Run before Friday opening to keep DB fast |
| `purge_logs.sh` — delete debug/session logs | ❌ Not done | Reduces table bloat |
| `daily_snapshot.sh` — save inventory totals only | ❌ Not done | Point-in-time inventory snapshot for reconciliation |
| `ingredient_rollup.py` — merge ingredient consumptions by day via Odoo shell | ❌ Not done | Aggregates phantom BoM explosions into daily summaries |
| Weekly physical inventory reminder/schedule | ❌ Not done | Documented in `docs/plan.md` but no automation |

## Phase 11 — AI-Suggested Improvements

> Additional ideas for operational excellence, not in original plans.

| Item | Status | Notes |
|------|--------|-------|
| POS payment methods (cash + MercadoPago/QR) | ❌ Not done | Critical for real operations; cash default, add digital options |
| Warehouse & stock location config in import script | ❌ Not done | Default warehouse assignment for proper inventory flow |
| Paper fallback procedure (documented) | ❌ Not done | Pre-printed order pads for when server is completely down |
| Multi-tier history retention (7d detail → daily → monthly) | ❌ Not done | Structured data lifecycle to balance traceability vs. performance |
| UPS monitoring script (check power status, alert on battery) | ❌ Not done | `ups_status.sh` — detect power loss and trigger protective measures |
| POS session auto-close at end of day | ❌ Not done | Prevents stale sessions accumulating overnight |
| Sales dashboard (most sold pizza, daily revenue, cost/margin) | ❌ Not done | Builds on existing cost prices in products.csv |
| Ingredient cost alert (threshold notification when cost changes) | ❌ Not done | Track supplier price changes to maintain margins |

---

## Summary

| Phase | Total Items | ✅ Done | ⚠️ Partial | ❌ Not Done |
|-------|-------------|---------|------------|-------------|
| 0 — Architecture Foundation | 9 | 9 | 0 | 0 |
| 1 — Core Operations | 17 | 15 | 0 | 2 |
| 2 — Employees & Roles | 5 | 0 | 0 | 5 |
| 3 — Hardware & Network | 8 | 4 | 0 | 4 |
| 4 — Backup & Reliability | 8 | 4 | 1 | 3 |
| 5 — Security | 8 | 3 | 1 | 4 |
| 6 — Customization & Reporting | 5 | 0 | 1 | 4 |
| 7 — E-commerce & Scaling | 3 | 0 | 0 | 3 |
| 8 — Printer & Kitchen Display | 6 | 0 | 0 | 6 |
| 9 — Emergency & Recovery Scripts | 9 | 0 | 1 | 8 |
| 10 — Performance & Maintenance | 7 | 0 | 0 | 7 |
| 11 — AI-Suggested Improvements | 8 | 0 | 0 | 8 |
| **Total** | **93** | **35** | **4** | **54** |

**Next priorities** (recommended order):
1. POS payment methods & warehouse setup (finish Phase 1)
2. Thermal printer + KDS setup (Phase 8) — kitchen can't work without tickets
3. `kitchen_panic.sh` + `ghostbuster.sh` (Phase 9) — highest emergency value
4. User roles: Manager, Cashier, Kitchen (Phase 2)
5. Cron job for automated backups + offsite push (Phase 4)
6. `compress_stock_moves.sh` + `vacuum_friday.sh` (Phase 10) — prevents DB bloat from phantom BoMs
7. HTTPS with Let's Encrypt or self-signed certs (Phase 5)