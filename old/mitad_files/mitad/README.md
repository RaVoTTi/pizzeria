# Mitad y Mitad — Half & Half Pizza System

## Architecture

```
POS Frontend                         Odoo Backend
─────────────                        ─────────────
Cashier taps [🍕 Mitad y Mitad]
       │
       ▼
pos_mitad_configurator (2-step wizard)
  ├─ Step 1: "Selecciona la 1ra Mitad" (tile grid)
  └─ Step 2: "Selecciona la 2da Mitad" (tile grid)
       │
       ▼
pos_half_pizza (MAX pricing)
  └─ Sets price = MAX(price_A, price_B)
       │
       ▼
Order synced to backend ──────────► setup_mitad_mitad.py
                                      ├─ Dynamic variant (on-demand, not 324 upfront)
                                      └─ Phantom BoM (conditional lines at 50% qty)
                                         └─ Stock deducted automatically
```

## Modules (POS Frontend)

### `pos_mitad_configurator/`
**2-step wizard UI.** Patches `ProductConfiguratorPopup` to show a tile grid instead of radio buttons. Step 1 selects Lado A, Step 2 selects Lado B. Uses Odoo's native configurator flow to create the correct variant with attribute values.

### `pos_half_pizza/`
**MAX pricing patch.** Overrides the POS line price to `MAX(price_of_pizza_A, price_of_pizza_B)`. Reads the selected attribute values from the order line's `product_template_attribute_value_ids`.

## Scripts (Backend — run via Odoo shell)

### `setup_mitad_mitad.py`
**Master setup script.** Runs all 6 steps in one sweep:
1. Finds all 18 pizzas and their phantom BoMs
2. Creates Lado A / Lado B attributes with `create_variant='dynamic'`
3. Creates attribute values for each pizza
4. Links attributes to the Mitad y Mitad product
5. Builds ptav map for BoM conditioning
6. Creates phantom BoM with conditional lines (50% qty per side)

Usage:
```bash
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo < addons/mitad/setup_mitad_mitad.py
```

### `step0_cleanup.py`
**Nuke button.** Removes all Mitad y Mitad attribute lines, attributes, BoMs, and server actions. Resets the product to a clean state.

### `complete_cleanup.py`
**Aggressive cleanup.** Deletes all variants, PTAVs, attribute lines, and BoMs for Mitad y Mitad.

### `remove_attributes.py`
Removes attributes and BoMs, reverting Mitad y Mitad to a simple product.

## Debug Scripts

Located in `debug_scripts/` — step-by-step equivalents of `setup_mitad_mitad.py` for learning/debugging:
- `step1_verify.py` — Prerequisite check
- `step2_attributes.py` — Create attributes
- `step3_link_attributes.py` — Link to product
- `step4_bom.py` — Create phantom BoM
- `step5_price_extra.py` — Set price extras
- `step6_verify.py` — End-to-end verification
