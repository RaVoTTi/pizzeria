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
| Import script (categories, products, BoMs, POS) | ✅ Done | `addons/import_pizzas.py` — 6-step pipeline |
| POS config name updated | ✅ Done | Sets name to "Pizzeria El Gordo" |
| Modules auto-installed (stock, mrp, point_of_sale) | ✅ Done | `import_pizzas.py` installs them before import |
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
| Thermal printer configuration | ❌ Not done | No ESC/POS or IoT box setup |
| Hardware actually procured | ❌ Not done | Physical hardware — outside code scope |

## Phase 4 — Backup & Reliability

> From: `docs/plan.md` Phase 5, `docs/history.md` Phase 6

| Item | Status | Notes |
|------|--------|-------|
| Backup script (pg_dump + 7-day retention) | ✅ Done | `scripts/backup.sh` |
| Restore script (with confirmation prompt) | ✅ Done | `scripts/restore.sh` |
| Odoo shell helper | ✅ Done | `scripts/odoo-shell.sh` |
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
| Kitchen Display System (KDS) | ❌ Not done | Future phase |
| Multi-location support | ❌ Not done | Future phase |
| Multiple POS terminals | ❌ Not done | Only one POS config defined |

---

## Summary

| Phase | Total Items | ✅ Done | ⚠️ Partial | ❌ Not Done |
|-------|-------------|---------|------------|-------------|
| 0 — Architecture Foundation | 9 | 9 | 0 | 0 |
| 1 — Core Operations | 13 | 10 | 0 | 3 |
| 2 — Employees & Roles | 5 | 0 | 0 | 5 |
| 3 — Hardware & Network | 7 | 4 | 0 | 3 |
| 4 — Backup & Reliability | 7 | 3 | 1 | 3 |
| 5 — Security | 8 | 3 | 1 | 4 |
| 6 — Customization & Reporting | 5 | 0 | 1 | 4 |
| 7 — E-commerce & Scaling | 4 | 0 | 0 | 4 |
| **Total** | **58** | **29** | **2** | **26** |

**Next priorities** (recommended order):
1. POS payment methods & warehouse setup (finish Phase 1)
2. User roles: Manager, Cashier, Kitchen (Phase 2)
3. Cron job for automated backups + offsite push (Phase 4)
4. Thermal printer / IoT box setup (Phase 3)
5. HTTPS with Let's Encrypt or self-signed certs (Phase 5)