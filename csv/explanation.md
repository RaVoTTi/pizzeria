CSV Overview & Connections
categories.csv
    │
    │  (categ_id/id references)
    ▼
products.csv
    │
    │  (product_tmpl_id/id references)
    ▼
┌─────────────────────────┐
│ receta_del_bollo.csv     │  ← Intermediate dough recipe
│ (makes "Bollo de Masa")  │     references raw ingredients
└───────────┬─────────────┘
            │
            │  (Bollo de Masa used as ingredient)
            ▼
┌─────────────────────────┐
│ receta_pizzas_con_masa.csv│ ← Pizza BoMs (phantom/kit type)
│ (all pizza recipes)       │    references Bollo + toppings
└─────────────────────────┘
producto_masa.csv  ← Just 1 product: the "Bollo" intermediate
unidades.csv       ← Custom UoM: "Pinta" (beer glass size)
File	What it does	Key field
categories.csv	10 categories in a tree (Todos → Gastos/Insumos/Ventas → subcategories)	id → referenced by products
products.csv	78 products: ingredients (kg/L), drinks, empanadas, pizzas, beer, delivery fee	id like ins_harina, piz_muzza
producto_masa.csv	1 intermediate product: "Bollo de Masa" (pre-pizza dough)	id = inter_bollo
receta_del_bollo.csv	3 lines: dough recipe (0.3kg flour + 0.18L water + 0.005kg yeast)	phantom BoM for inter_bollo
receta_pizzas_con_masa.csv	82 lines: all pizza BoMs, each line = 1 ingredient per pizza, references Bollo + toppings	product_tmpl_id/id + bom_line_ids/product_id by name
unidades.csv	1 custom UoM: "Pinta" (beer glass, ~0.473L)	id = uom_pinta
recipes.csv	Empty — unused	 
The connection chain
Flour, Water, Yeast ──→ receta_del_bollo ──→ Bollo de Masa
                                                    │
                                                    ▼
Mozzarella + Salsa + Bollo ──→ receta_pizzas_con_masa ──→ Pizza Mozzarella
All pizza recipes follow the phantom/kit BoM pattern: when you sell a pizza in POS, Odoo automatically deducts the raw ingredients (no manual manufacturing orders needed).