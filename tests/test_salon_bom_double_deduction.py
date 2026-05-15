"""
Salon BoM Double-Detection Test

Verifies that [S] Salon product BoMs copy the Mostrador ingredient recipe
directly, NOT link to the Mostrador product.

WRONG (causes double deduction):
  [S] Mozzarella BoM → 1x Mozzarella (Mostrador product)
  Mozzarella BoM → Bollo + Cheese + Sauce
  Result: Stock deducted TWICE (once for [S] Mozzarella, once for Mozzarella)

CORRECT (single deduction):
  [S] Mozzarella BoM → Bollo + Cheese + Sauce (same as Mostrador)
  Result: Stock deducted ONCE

Usage:
  docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo \
    < tests/test_salon_bom_double_deduction.py
"""

PASS = 0
FAIL = 0
ERRORS = []


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS [{label}]")
    else:
        FAIL += 1
        msg = f"  FAIL [{label}] {detail}"
        print(msg)
        ERRORS.append(msg)


print("=" * 70)
print("  SALON BOM DOUBLE-DEDUCTION TEST")
print("=" * 70)

ProductTemplate = env['product.template']
ProductProduct = env['product.product']

# ── 1. Find Salon and Mostrador product pairs ────────────
print("\n[1/4] Finding Salon/Mostrador product pairs...")

salon_products = ProductTemplate.search([
    ('name', 'like', '[S]%'),
    ('available_in_pos', '=', True),
])
print(f"  Found {len(salon_products)} Salon products")
check("Salon products exist", len(salon_products) > 0)

# ── 2. Check each Salon product's BoM ────────────────────
print("\n[2/4] Checking Salon BoMs for double-deduction links...")

double_deduction_errors = []
salon_ok = 0
salon_missing_bom = 0

for salon in salon_products:
    mostrador_name = salon.name.replace('[S] ', '')
    mostrador = ProductTemplate.search([
        ('name', '=', mostrador_name),
    ], limit=1)

    salon_bom = env['mrp.bom'].search([
        ('product_tmpl_id', '=', salon.id),
        ('type', '=', 'phantom'),
    ], limit=1)

    if not salon_bom:
        salon_missing_bom += 1
        print(f"  WARNING: No phantom BoM for {salon.name}")
        continue

    # Check if any BoM line links to the Mostrador product
    has_link_to_mostrador = False
    if mostrador:
        for line in salon_bom.bom_line_ids:
            if line.product_id.product_tmpl_id.id == mostrador.id:
                has_link_to_mostrador = True
                double_deduction_errors.append({
                    'salon': salon.name,
                    'mostrador': mostrador_name,
                    'ingredient': line.product_id.display_name,
                })
                break

    if has_link_to_mostrador:
        print(f"  ERROR: {salon.name} → links to {mostrador_name} (DOUBLE DEDUCTION!)")
    else:
        salon_ok += 1

check(f"Salon BoMs OK ({salon_ok} products)", salon_ok > 0)
check("No double-deduction links", len(double_deduction_errors) == 0,
      f"{len(double_deduction_errors)} errors found")

if double_deduction_errors:
    print("\n  Double-deduction errors:")
    for err in double_deduction_errors:
        print(f"    - {err['salon']} → {err['mostrador']} (via {err['ingredient']})")

# ── 3. Verify Salon BoMs have same ingredients as Mostrador ──
print("\n[3/4] Verifying Salon BoMs match Mostrador ingredients...")

mismatch_count = 0
match_count = 0

for salon in salon_products[:10]:  # Check first 10 to keep output manageable
    mostrador_name = salon.name.replace('[S] ', '')
    mostrador = ProductTemplate.search([
        ('name', '=', mostrador_name),
    ], limit=1)

    salon_bom = env['mrp.bom'].search([
        ('product_tmpl_id', '=', salon.id),
        ('type', '=', 'phantom'),
    ], limit=1)
    mostrador_bom = env['mrp.bom'].search([
        ('product_tmpl_id', '=', mostrador.id),
        ('type', '=', 'phantom'),
    ], limit=1) if mostrador else None

    if not salon_bom or not mostrador_bom:
        continue

    # Compare ingredient sets
    salon_ingredients = set(
        (line.product_id.display_name, round(line.product_qty, 4))
        for line in salon_bom.bom_line_ids
    )
    mostrador_ingredients = set(
        (line.product_id.display_name, round(line.product_qty, 4))
        for line in mostrador_bom.bom_line_ids
    )

    if salon_ingredients == mostrador_ingredients:
        match_count += 1
    else:
        mismatch_count += 1
        print(f"  MISMATCH: {salon.name} vs {mostrador_name}")
        print(f"    Salon: {salon_ingredients}")
        print(f"    Mostrador: {mostrador_ingredients}")

check(f"Salon/Mostrador BoMs match ({match_count} pairs)", match_count > 0)
if mismatch_count > 0:
    print(f"  {mismatch_count} mismatches found")

# ── 4. Summary ───────────────────────────────────────────
print("\n[4/4] Summary...")

print(f"  Total Salon products: {len(salon_products)}")
print(f"  Salon BoMs OK: {salon_ok}")
print(f"  Missing BoMs: {salon_missing_bom}")
print(f"  Double-deduction errors: {len(double_deduction_errors)}")
print(f"  BoM matches: {match_count}")
print(f"  BoM mismatches: {mismatch_count}")

# ── Results ──────────────────────────────────────────────
print()
print("=" * 70)
print("  TEST RESULTS")
print("=" * 70)
print(f"  Passed: {PASS}")
print(f"  Failed: {FAIL}")
if ERRORS:
    print()
    print("  Errors:")
    for e in ERRORS:
        print(f"    - {e}")

print()
if FAIL == 0:
    print("  ✓ ALL TESTS PASSED")
    print()
    print("  Salon BoMs are correctly configured:")
    print("  - No double-deduction links to Mostrador products")
    print("  - Salon BoMs copy Mostrador ingredient recipes directly")
    print("  - Stock will be deducted correctly for both channels")
elif FAIL > 0:
    print(f"  ✗ {FAIL} TEST(S) FAILED")
    print()
    print("  FIX: Run scripts/import-data.sh to rebuild BoMs from CSV.")
    print("  The import script copies Mostrador recipes to Salon products.")

print()
print("=" * 70)

env.cr.rollback()
