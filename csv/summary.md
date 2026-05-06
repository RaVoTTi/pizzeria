# CSV Data Summary

## Files Overview

| File | Records | Purpose |
|------|---------|---------|
| `categories.csv` | 11 categories | Hierarchical product category tree |
| `products.csv` | 78 products | Ingredients, drinks, empanadas, pizzas, beer, delivery |
| `producto_masa.csv` | 1 product | "Bollo de Masa" (intermediate dough) |
| `unidades.csv` | 1 UoM | "Pinta" (beer glass, ~0.473L, factor_inv=2) |
| `receta_del_bollo.csv` | 3 lines | Phantom BoM: Flour + Water + Yeast → Bollo |
| `receta_pizzas_con_masa.csv` | 82 lines | 20 pizza phantom BoMs (each references Bollo + toppings) |
| `recipes.csv` | 0 | Empty/unused |
| `unidades-smaller.csv` | 1 | Alternative Pinta UoM (unused) |

---

## Connection Chain

```
Flour (0.3kg) ──┐
Water (0.18L) ──┼──→ receta_del_bollo ──→ Bollo de Masa (intermediate)
Yeast (0.005kg) ┘                               │
                                                 ▼
Bollo (1) + Muzzarella (0.28) + Salsa (0.1) ──→ receta_pizzas_con_masa ──→ Pizza Mozzarella
```

All pizza recipes follow **phantom/kit BoM** pattern: POS sale auto-deducts raw ingredients.

---

## categories.csv

| id | name | parent |
|----|------|--------|
| cat_all | Todos | - |
| cat_gastos | GASTOS OPERATIVOS | cat_all |
| cat_servicios | Servicios (Luz/Gas) | cat_gastos |
| cat_insumos | INSUMOS | cat_all |
| cat_barriles | Barriles y Gas | cat_insumos |
| cat_mp | Materia Prima Cocina | cat_insumos |
| cat_venta | VENTAS | cat_all |
| cat_bebidas | Bebidas sin Alcohol | cat_venta |
| cat_birra_venta | Cerveza Barra | cat_venta |
| cat_pizzas | Pizzas | cat_venta |
| cat_delivery | Deliveries | cat_venta |

---

## products.csv — 78 Products

### Raw Ingredients (Materia Prima Cocina, id prefix: `ins_`)
All type=product, cost > 0, list_price=0 (not sold directly):

| id | name | UoM | Cost |
|----|------|-----|------|
| ins_harina | Harina 0000 | kg | 800 |
| ins_levadura | Levadura Fresca | kg | 1500 |
| ins_agua | Agua Filtrada | L | 50 |
| ins_aceite | Aceite de Oliva | L | 8000 |
| ins_sal | Sal Fina | kg | 400 |
| ins_muzza | Muzzarella Cilindro | kg | 6500 |
| ins_salsa | Salsa de Tomate Base | L | 2000 |
| ins_provolone | Queso Provolone | kg | 9000 |
| ins_roquefort | Queso Roquefort | kg | 11000 |
| ins_parmesano | Queso Parmesano Rallado | kg | 15000 |
| ins_jamon | Jamón Cocido Natural | kg | 7000 |
| ins_morron | Morrones en Conserva | kg | 5000 |
| ins_aceituna | Aceitunas Verdes | kg | 4500 |
| ins_panceta | Panceta Ahumada (Bacon) | kg | 12000 |
| ins_champi | Champiñones Frescos | kg | 8000 |
| ins_anana | Ananá en Rodajas | kg | 6000 |
| ins_peperoni | Pepperoni Rodajas | kg | 18000 |
| ins_rucula | Rúcula Fresca | kg | 3000 |
| ins_tomate_c | Tomates Cherry | kg | 4000 |
| ins_albahaca | Albahaca Fresca | kg | 5000 |
| ins_huevo | Huevos Maple | Unidades | 150 |
| ins_ajo | Ajo Triturado | kg | 3000 |
| ins_cebolla | Cebolla Blanca | kg | 800 |
| ins_jamon_crudo | Jamón Crudo | kg | 18000 |
| ins_palmitos | Palmitos (Lata/Kg) | kg | 12000 |
| ins_anchoas | Anchoas (Filet) | kg | 25000 |
| ins_pesto | Salsa Pesto (Casera) | kg | 8000 |

### Kegs & Gas (Barriles y Gas)
| id | name | UoM | Cost |
|----|------|-----|------|
| ins_co2 | Tubo CO2 (Carga) | kg | 15000 |
| ins_golden_bulk | Cerveza Golden (A granel) | L | 2500 |
| ins_roja_bulk | Cerveza Roja (A granel) | L | 2600 |
| ins_negra_bulk | Cerveza Negra (A granel) | L | 2700 |

### Soft Drinks (Bebidas sin Alcohol) — all in Unidades
Coca-Cola, Coca-Cola Zero, Sprite, Fanta, Pepsi, 7up, Agua — each in 1.5L and 2.25L formats.
Cost: 1000–2500 | Price: 2000–4500

### Empanadas (VENTAS category)
| id | name | Price |
|----|------|-------|
| emp_carne | Empanada Carne | 1200 |
| emp_jyq | Empanada Jamón y Queso | 1200 |
| emp_verdura | Empanada Verdura | 1200 |
| emp_matambre | Empanada Matambrito | 1400 |
| emp_cheesa | Empanada Cheeseburger | 1400 |
| emp_pollo | Empanada Pollo | 1300 |

### Pizzas (Pizzas category) — all price > 0
| id | name | Price |
|----|------|-------|
| piz_muzza | Mozzarella | 12000 |
| piz_especial | Especial | 14000 |
| piz_4q_ahum | Cuatro quesos ahumado | 14000 |
| piz_rucula_cru | Rucula y jamon crudo | 14000 |
| piz_rucula_veg | Rucula veggie | 14000 |
| piz_napo_ajo | Napolitana con ajo | 14000 |
| piz_napo_veg | Napolitana vegana | 14000 |
| piz_peperoni | Pepperoni | 14000 |
| piz_fugazzeta | Fugazzeta | 14000 |
| piz_grinch | Grinch (fugazzeta con pesto) | 14000 |
| piz_caprese | Caprese | 17000 |
| piz_borromeo | Borromeo (panceta) | 17000 |
| piz_super_pesto | Super Pesto | 17000 |
| piz_champi | Champignon | 17000 |
| piz_champi_veg | Champignon veggie | 17000 |
| piz_palmitos | Palmitos y jamon | 18000 |
| piz_anana | Anana | 18000 |
| piz_anchoas | Anchoas | 18000 |
| piz_super_gordo | Super gordo (fugazzeta rellena) | 27000 |
| promo_2_muzza | PROMO 2 Mozzarellas | 22000 |
| piz_mitad_mitad | Mitad y Mitad | 12000 |

### Beer (Cerveza Barra)
| id | name | UoM | Price |
|----|------|-----|-------|
| venta_pinta_gold | Pinta Golden | Pinta | 4500 |
| venta_litro_gold | Recarga 1 Litro Golden | Unidades | 8000 |
| venta_pinta_roja | Pinta Roja | Pinta | 4800 |
| venta_litro_roja | Recarga 1 Litro Roja | Unidades | 8500 |
| venta_pinta_negra | Pinta Negra | Pinta | 5000 |
| venta_litro_negra | Recarga 1 Litro Negra | Unidades | 9000 |

### Delivery
| id | name | Price |
|----|------|-------|
| serv_delivery | Costo de Envío | 1500 |

---

## producto_masa.csv — 1 Product

| id | name | category | type | UoM | Cost | Price |
|----|------|----------|------|-----|------|-------|
| inter_bollo | Bollo de Masa (Pre-pizza) | cat_mp | product | Units | 0 | 0 |

Not sold directly — intermediate used in all pizza BoMs.

---

## receta_del_bollo.csv — Bollo de Masa BoM (Phantom)

| Ingredient | Qty |
|------------|-----|
| Harina 0000 | 0.3 kg |
| Agua Filtrada | 0.18 L |
| Levadura Fresca | 0.005 kg |

Code: "Fórmula Masa Base"

---

## receta_pizzas_con_masa.csv — Pizza BoMs (Phantom)

All pizzas have a phantom BoM. Each pizza uses 1 Bollo + specific toppings.
Notable recipes:

| Pizza | Ingredients (besides Bollo=1) |
|-------|------------------------------|
| Mozzarella | Muzzarella 0.28, Salsa 0.1, Aceitunas 0.05 |
| Especial | Muzzarella 0.28, Salsa 0.1, Jamón 0.1, Morrones 0.05 |
| 4 Quesos Ahumado | Muzzarella 0.15, Provolone 0.05, Roquefort 0.05, Parmesano 0.05 |
| Fugazzeta | Muzzarella 0.3, Cebolla 0.25 |
| Super Gordo | **2** Bollo, Muzzarella 0.6, Cebolla 0.3, Jamón 0.2 |
| Promo 2 Muzzas | **2** Bollo, Muzzarella 0.56, Salsa 0.2, Aceitunas 0.1 |

When 1 pizza is sold, the full chain expands: Pizza → Bollo → Flour + Water + Yeast → all deducted from stock.

---

## unidades.csv — Custom UoM

| id | name | category | type | factor_inv | rounding |
|----|------|----------|------|------------|----------|
| uom_pinta | Pinta | Volumen | Volumen | 2 | 0.01 |

1 Pinta = 0.473 L (factor_inv=2 implies 1/factor=0.5, adjusted in import script to 0.473)
