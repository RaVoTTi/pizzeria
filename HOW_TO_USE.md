# Pizzeria El Gordo — Setup & Usage Guide

## Quick Start (Complete Fresh Setup)

For a complete fresh installation:

```bash
cd ~/Documents/odoo-pizzeria

# 1. Stop and clean everything
docker compose down
docker volume rm -f odoo-pizzeria_odoo-db-data odoo-pizzeria_odoo-web-data

# 2. Start the stack
docker compose up -d

# 3. Wait for database to be ready (~15 seconds)
sleep 15

# 4. Initialize database and install modules
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i base,stock,mrp,point_of_sale,pos_restaurant --stop-after-init

# 5. Import data
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_products.py

# 6. Optional: Setup restaurant floor plans
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py

# 7. Optional: Setup Mitad y Mitad (half & half pizzas)
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_mitad_mitad.py

# 8. Access Odoo at http://elgordo.local (admin password in config/odoo.conf)
```

**After first login:**
1. Set language to Spanish (see Section 8)
2. Create/open a POS session
3. Products should appear. If not, clear browser cache (Ctrl+R)

---

## Architecture

```
Tablet (POS) ──→ Nginx (:80) ──→ Odoo (:8069) ──→ PostgreSQL (:5432)
                                [elgordo.local]
```

| Component | Image | Network |
|-----------|-------|---------|
| Nginx | `nginx:alpine` | `frontend` |
| Odoo 19 | `odoo:19.0` | `frontend`, `backend` |
| PostgreSQL | `postgres:16` | `backend` (internal only) |

**Access:** `http://elgordo.local` or `http://192.168.1.100`

Credentials are in `.env` (gitignored). The Odoo admin password is in `config/odoo.conf`.

---

## 1. Setup Steps

### Option A: Automated Setup (Recommended)

Run the full setup script:

```bash
cd ~/Documents/odoo-pizzeria
./scripts/reset-and-setup.sh
```

### Option B: Manual Step-by-Step

```bash
cd ~/Documents/odoo-pizzeria

# Start the stack
docker compose up -d

# Initialize database
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo -i base --stop-after-init

# Install required modules
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i stock,mrp,point_of_sale,pos_restaurant --stop-after-init

# Restart
docker compose up -d
```

Wait until Odoo is reachable at `http://elgordo.local`, then proceed to import data.

> **Upgrading from Odoo 18?** Requires a full database reset. Odoo 19 has incompatible schema changes. Follow the "Reset Database" steps in Section 5 first.

---

## 2. Import Scripts Reference

| Order | Script | Purpose | Source Data |
|-------|--------|---------|-------------|
| 1 | `import_initial.py` | Install modules, create UoMs | `csv/unidades.csv` |
| 2 | `import_products.py` | **Main import** - Categories, products, BoMs, POS setup | `csv/categories.csv`, `csv/products.csv`, `csv/producto_masa.csv`, `csv/receta_del_bollo.csv`, `csv/receta_pizzas_con_masa.csv` |
| 3 | `setup_floors.py` | **Optional** - Restaurant floor plans with tables | `images/salon.png`, `images/afuera.png` |
| 4 | `setup_mitad_mitad.py` | Setup half & half pizza (Mitad y Mitad) with attributes and automation | Existing pizza products and BoMs |

**Run in order:**
```bash
# Required
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_products.py

# Optional - floor plans and mitad y mitad
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_mitad_mitad.py
```

---

## 3. What's Imported

### Products (80 total)
- **Raw ingredients** (flour, cheese, sauce, toppings)
- **20 Pizzas** (Mozzarella, Especial, 4 Quesos, etc.)
- **🍕 Mitad y Mitad** - Half & half pizza with 289 combinations
- **Drinks** (Coca-Cola, Sprite, Fanta, Pepsi, water)
- **6 Empanadas** (Carne, JyQ, Verdura, etc.)
- **Beer products** (Pintas and 1L refills)

### 🍕 Mitad y Mitad (Half & Half Pizza)

Special product that allows customers to order **half one pizza + half another**:

**How it works:**
1. Tap "🍕 Mitad y Mitad" in POS
2. Select **Lado A** (Side A) - choose from 17 available pizzas
3. Select **Lado B** (Side B) - choose from 17 available pizzas
4. Price automatically calculates to **MAX(price_A, price_B)**
   - Example: Mozzarella (12000) + Pepperoni (14000) = **14000**
   - You pay for the more expensive half

**Stock deduction:**
- Automatically deducts **50%** of ingredients from Side A's pizza
- Automatically deducts **50%** of ingredients from Side B's pizza
- Full dough (Bollo de Masa) always deducted (1 unit)

**Excluded from halves:**
- PROMO 2 Mozzarellas (promotional item)
- Super Gordo (stuffed pizza - different base)

**Available for halves:**
Mozzarella, Especial, 4 Quesos Ahumado, Rúcula y Jamón Crudo, Rúcula Veggie, Napolitana con Ajo, Napolitana Vegana, Pepperoni, Fugazzeta, Grinch, Caprese, Borromeo, Super Pesto, Champignon, Champignon Veggie, Palmitos y Jamón, Ananá, Anchoas

### POS Setup (Automatic)
- ✅ Products enabled for POS (`available_in_pos = True`)
- ✅ 4 POS categories created: **Pizzas, Cerveza, Bebidas, Empanadas**
- ✅ Demo products hidden (no more "Spicy Tuna Sandwich")
- ✅ Products organized by category

### Inventory
- **Phantom BoMs** - Auto-deduct ingredients when selling pizzas
- **Bollo de Masa** - Shared dough recipe for all pizzas
- **Custom UoM** - "Pinta" for beer glasses (~0.473L)

---

## 4. Restaurant Floor Plans (Optional)

Set up visual table management:

```bash
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py
```

| Floor | Tables | Description |
|-------|--------|-------------|
| **Salón** | 1-12 | Indoor dining room |
| **Afuera** | 13-16, R1-R3 | Outdoor terrace with 3 round tables |

**Features:**
- Visual floor plan with table positions
- Click tables to open orders
- Track occupied tables
- Split bills by table

**To customize:** Edit `addons/setup_floors.py` or use UI: **Point of Sale → Configuration → Restaurant → Floors**

---

## 5. Complete Reset & Rebuild (Nuclear Option)

**⚠️ WARNING: This will delete ALL data permanently!**

Use this when you want a completely fresh start with everything configured from scratch.

### Step 1: Stop Everything

```bash
cd ~/Documents/odoo-pizzeria

# Stop all containers
docker compose down

# Remove all data volumes (THIS DELETES ALL DATA!)
docker volume rm -f odoo-pizzeria_odoo-db-data odoo-pizzeria_odoo-web-data

# Clean up any leftover containers
docker system prune -f
```

### Step 2: Full Rebuild with All Products & Layouts

```bash
# 1. Start the stack
docker compose up -d

# 2. Wait for database to be ready
echo "Waiting for database..."
sleep 20

# 3. Initialize and install all modules
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i base,stock,mrp,point_of_sale,pos_restaurant --stop-after-init

# 4. Import all data (units, categories, products, BoMs, POS config)
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_products.py

# 5. Setup restaurant floor plans with images
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py

# 6. Setup Mitad y Mitad (half & half pizzas)
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_mitad_mitad.py

# 7. Restart to ensure everything is loaded
docker compose restart web

echo "================================"
echo "Setup complete!"
echo "Access: http://elgordo.local"
echo "Admin password: see config/odoo.conf"
echo "================================"
```

### Alternative: One-Command Complete Reset

Save this as `scripts/nuclear-reset.sh`:

```bash
#!/bin/bash
set -e

echo "🧨 NUCLEAR RESET - Deleting everything..."
cd ~/Documents/odoo-pizzeria

echo "📦 Creating backup just in case..."
./scripts/backup.sh 2>/dev/null || echo "No backup script found, continuing..."

echo "🛑 Stopping containers..."
docker compose down
docker volume rm -f odoo-pizzeria_odoo-db-data odoo-pizzeria_odoo-web-data 2>/dev/null || true
docker system prune -f

echo "🚀 Starting fresh..."
docker compose up -d

echo "⏳ Waiting for database (20s)..."
sleep 20

echo "🔧 Installing modules..."
docker compose run --rm web odoo server -c /etc/odoo/odoo.conf -d elgordo \
  -i base,stock,mrp,point_of_sale,pos_restaurant --stop-after-init

echo "📥 Importing data..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_initial.py
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_products.py

echo "🗺️  Setting up floor plans..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_floors.py

echo "🍕 Setting up Mitad y Mitad (half & half pizzas)..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/setup_mitad_mitad.py

echo "🔄 Restarting..."
docker compose restart web

echo ""
echo "✅ COMPLETE! Your pizzeria is ready:"
echo "   URL: http://elgordo.local"
echo "   Products: 79 (pizzas, drinks, empanadas)"
echo "   Tables: 19 (Salón + Afuera)"
echo ""
echo "Next steps:"
echo "1. Open browser to http://elgordo.local"
echo "2. Log in as admin (password in config/odoo.conf)"
echo "3. Set language to Spanish (Section 8)"
echo "4. Open POS session"
echo "5. Hard refresh: Ctrl+Shift+R"
```

Then run: `chmod +x scripts/nuclear-reset.sh && ./scripts/nuclear-reset.sh`

### What Gets Created:

| Component | Count | Details |
|-----------|-------|---------|
| **Products** | 80 | 20 pizzas (including Mitad y Mitad), 6 empanadas, 14 drinks, beer, ingredients |
| **Categories** | 11 | Full hierarchy (Todos → VENTAS, INSUMOS, etc.) |
| **POS Categories** | 4 | Pizzas, Cerveza, Bebidas, Empanadas |
| **BoMs** | 21 | Phantom BoMs for auto-ingredient deduction |
| **Mitad y Mitad Variants** | 289 | 17 pizzas × 17 pizzas (half & half combinations) |
| **Automated Actions** | 2 | MAX pricing + 50% stock deduction |
| **Tables** | 19 | Salón (1-12) + Afuera (13-16 + 3 round) |
| **Floor Plans** | 2 | With background images from `images/` |

---

## 6. Backup & Restore

```bash
# Backup (nightly recommended — 7-day retention)
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh backups/odoo_db_20260430_030000.sql.gz
```

Backups are stored in `backups/` as gzipped SQL dumps.

> **Note:** Backups are local only. Copy `backups/` to external media regularly.

---

## 7. Odoo Shell

```bash
./scripts/odoo-shell.sh
```

Or directly:
```bash
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo
```

**Useful commands:**
```python
env['product.template'].search([])      # List all products
env['product.category'].search([])       # List all categories
env['mrp.bom'].search([])                # List all BoMs
env['restaurant.floor'].search([])       # List floor plans
self.env.cr.commit()                     # Save changes
```

---

## 8. Language Configuration (Spanish)

### Via UI (Recommended)

1. Log in to `http://elgordo.local` (admin password in `config/odoo.conf`)

2. **Install Spanish:**
   - Go to **Settings → Translations → Languages**
   - Find "Spanish (ES) / Español (ES)"
   - Click **Activate**

3. **Set User Language:**
   - Click your username (top-right)
   - Go to **Preferences**
   - Change **Language** to "Spanish (ES)"
   - **Save** and **re-log**

---

## 9. Troubleshooting

### Products Not Showing in POS?

**Quick fix:** Re-run the import script
```bash
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/import_products.py
```

Then: Close POS tab → Refresh browser (Ctrl+R) → Reopen POS

### Demo Products Still Showing?

If you see "Spicy Tuna Sandwich", "Burger", etc.:

**Via Shell:**
```bash
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo
```
```python
# Hide demo products
demo_categs = env['product.category'].search([('name', 'in', ['Food', 'Services'])])
demo_products = env['product.template'].search([
    ('categ_id', 'in', demo_categs.ids),
    ('available_in_pos', '=', True)
])
demo_products.write({'available_in_pos': False})
env.cr.commit()
```

### Common Issues

| Problem | Solution |
|---------|----------|
| `elgordo.local` not resolving | Add `192.168.1.100 elgordo.local` to hosts file |
| Odoo not starting | Check `docker compose logs web` |
| Can't modify floors | Close all POS sessions first |
| Products not appearing | Clear browser cache (Ctrl+R) |

---

## 10. Product Categories

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

- **INSUMOS** = raw ingredients (not sold directly)
- **VENTAS** = products available in POS
- **POS Categories** = Pizzas, Cerveza, Bebidas, Empanadas (for UI organization)

---

## 11. Known Risks

- **Stock drift** — Run weekly **Physical Inventory** adjustments
- **No offline fallback** — Keep paper backup if server dies
- **No RBAC** — All users currently have admin access
- **Local-only backups** — Copy `backups/` to external media regularly

---

## 12. How Phantom BoMs Work

Pizzas use **phantom/kit BoMs** — ingredients auto-deduct on sale:

```
Flour + Water + Yeast ──→ Bollo de Masa (phantom)
                                    │
                                    ▼
Bollo + Cheese + Sauce ──→ Pizza (phantom)
```

- No manufacturing orders needed
- Stock tracked only for **raw ingredients**
- Kitchen works faster!
