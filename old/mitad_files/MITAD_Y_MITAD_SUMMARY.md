# Mitad y Mitad Implementation Summary

## Overview
Implemented the "Half & Half Pizza" (Mitad y Mitad) feature for Pizzeria El Gordo POS system.

## What Was Implemented

### 1. Product Definition
- **File:** `csv/products.csv`
- **Added:** `piz_mitad_mitad,🍕 Mitad y Mitad,cat_pizzas,product,Unidades,0,12000,`
- Base price: 12000 (cheapest pizza - Mozzarella)

### 2. Setup Script
- **File:** `addons/setup_mitad_mitad.py` (455 lines)
- **Purpose:** Creates attributes, values, and automated actions

**Features:**
- Creates 2 attributes: "Lado A" and "Lado B" (radio buttons)
- Creates 17 attribute values per attribute (one for each eligible pizza)
- Links attributes to Mitad y Mitad product
- Odoo auto-generates 289 variants (17 × 17 combinations)
- Creates 2 automated actions:
  1. **MAX Pricing** - Corrects price to max(price_A, price_B) on order create/update
  2. **Stock Deduction** - Deducts 50% of ingredients from each side on payment

**Eligible pizzas (17 total):**
Mozzarella, Especial, 4 Quesos Ahumado, Rúcula y Jamón Crudo, Rúcula Veggie, Napolitana con Ajo, Napolitana Vegana, Pepperoni, Fugazzeta, Grinch, Caprese, Borromeo, Super Pesto, Champignon, Champignon Veggie, Palmitos y Jamón, Ananá, Anchoas

**Excluded:**
- PROMO 2 Mozzarellas (promotional)
- Super Gordo (stuffed pizza, different structure)

### 3. Nuclear Reset Integration
- **File:** `scripts/nuclear-reset.sh`
- **Added:** Step 4/4 to run `setup_mitad_mitad.py`
- Updated completion message to reflect new features

### 4. Documentation Updates
- **File:** `HOW_TO_USE.md`
- Updated product count (79 → 80)
- Added Mitad y Mitad section with detailed usage instructions
- Updated import scripts reference table
- Updated "What Gets Created" table with new components
- Updated all manual setup instructions

## How It Works

### POS Workflow
1. Cashier taps "🍕 Mitad y Mitad" in POS
2. Popup opens with 2 selectors:
   - **Lado A:** Select first pizza (17 options)
   - **Lado B:** Select second pizza (17 options)
3. Price auto-calculates: `MAX(price_A, price_B)`
   - Example: Mozzarella (12000) + Pepperoni (14000) = **14000**
4. Kitchen sees order with both sides specified
5. When payment is processed:
   - 50% of Side A's ingredients deducted from stock
   - 50% of Side B's ingredients deducted from stock
   - Full dough (Bollo de Masa) deducted for each pizza sold

### Stock Deduction Example
Customer orders: Mitad y Mitad with Mozzarella (A) + Pepperoni (B)

**Ingredients deducted:**
- 1 Bollo de Masa (full dough)
- 50% of Mozzarella toppings:
  - 0.14 kg Muzzarella Cilindro
  - 0.05 L Salsa de Tomate
  - 0.025 kg Aceitunas Verdes
- 50% of Pepperoni toppings:
  - 0.14 kg Muzzarella Cilindro
  - 0.05 L Salsa de Tomate
  - 0.04 kg Pepperoni Rodajas

**Total cheese:** 0.28 kg (normal for 1 pizza)
**Total sauce:** 0.10 L (normal for 1 pizza)
**Plus:** Pepperoni slices from Side B

## Technical Implementation

### Automated Actions Created
1. **Mitad y Mitad - MAX Pricing**
   - Trigger: On POS order creation and update
   - Action: Reads variant attributes, calculates MAX price, updates order line

2. **Mitad y Mitad - Stock Deduction**
   - Trigger: On POS order state change to "paid"
   - Action: 
     - Reads variant attributes to determine selected pizzas
     - Finds each pizza's phantom BoM
     - Creates stock moves at 50% quantity for each BoM line
     - Marks moves as done

### Database Objects Created
- 2 product attributes (`product.attribute`)
- 34 attribute values (`product.attribute.value`)
- 289 product variants (`product.product`)
- 2 attribute lines (`product.template.attribute.line`)
- 2 server actions (`ir.actions.server`)
- 3 base automation rules (`base.automation`)

## Testing Checklist

- [ ] Run `./scripts/nuclear-reset.sh` successfully
- [ ] Verify "🍕 Mitad y Mitad" appears in POS
- [ ] Tap Mitad y Mitad → verify variant selector popup appears
- [ ] Select Mozzarella (A) + Pepperoni (B)
- [ ] Verify price = 14000 (MAX pricing)
- [ ] Complete order and pay
- [ ] Verify stock deducted correctly (check Inventory app)
- [ ] Verify kitchen ticket shows both sides

## Files Modified
1. `csv/products.csv` - Added product definition
2. `addons/setup_mitad_mitad.py` - New setup script (455 lines)
3. `scripts/nuclear-reset.sh` - Added Step 4/4
4. `HOW_TO_USE.md` - Updated documentation

## Next Steps for Deployment

1. **Backup current data:**
   ```bash
   ./scripts/backup.sh
   ```

2. **Test in development:**
   ```bash
   ./scripts/nuclear-reset.sh
   ```

3. **Verify in POS:**
   - Open http://elgordo.local
   - Start POS session
   - Test Mitad y Mitad functionality

4. **Train staff:**
   - Explain MAX pricing rule
   - Show variant selector popup
   - Demonstrate kitchen ticket display
