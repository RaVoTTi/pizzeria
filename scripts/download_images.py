import os
import requests

API_KEY = "YOUR_ICONS8_API_KEY_HERE"
STYLE = "color"
SIZE = 100
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")

products = {
    # Soft Drinks (1.5L)
    "gas_coca_15": "coca cola bottle red",
    "gas_coca_225": "coca cola bottle red large",
    "gas_coca_z_15": "coca cola zero bottle black",
    "gas_coca_z_225": "coca cola zero bottle black large",
    "gas_sprite_15": "sprite bottle green",
    "gas_sprite_225": "sprite bottle green large",
    "gas_fanta_15": "fanta bottle orange",
    "gas_fanta_225": "fanta bottle orange large",
    "gas_pepsi_15": "pepsi bottle blue",
    "gas_pepsi_225": "pepsi bottle blue large",
    "gas_7up_15": "7up bottle green",
    "gas_7up_225": "7up bottle green large",
    "gas_agua_cg_15": "sparkling water bottle blue bubbles",
    "gas_agua_sg_15": "still water bottle blue drop",

    # Empanadas
    "emp_carne": "empanada meat",
    "emp_jyq": "empanada ham cheese",
    "emp_verdura": "empanada spinach vegetable",
    "emp_matambre": "empanada steak",
    "emp_cheesa": "empanada cheeseburger",
    "emp_pollo": "empanada chicken",

    # Pizzas
    "piz_muzza": "mozzarella pizza slice cheese",
    "piz_especial": "pizza slice ham peppers",
    "piz_4q_ahum": "four cheese pizza slice smoked",
    "piz_rucula_cru": "rucula prosciutto pizza slice",
    "piz_rucula_veg": "rucula tomato pizza slice vegetable",
    "piz_napo_ajo": "napolitana pizza tomato garlic",
    "piz_napo_veg": "vegan napolitana pizza tomato",
    "piz_peperoni": "pepperoni pizza slice",
    "piz_fugazzeta": "fugazzeta pizza onion",
    "piz_grinch": "pesto onion pizza slice",
    "piz_caprese": "caprese pizza mozzarella tomato basil",
    "piz_borromeo": "bacon pizza slice",
    "piz_super_pesto": "pesto pizza slice green",
    "piz_champi": "mushroom pizza slice",
    "piz_champi_veg": "mushroom pizza slice vegetable",
    "piz_palmitos": "heart of palm ham pizza slice",
    "piz_anana": "pineapple pizza slice",
    "piz_anchoas": "anchovy pizza slice",
    "piz_super_gordo": "stuffed pizza slice double",
    "promo_2_muzza": "two pizza slices promo",
    "piz_mitad_mitad": "half half pizza slice",
}

SEARCH_URL = "https://search.icons8.com/api/iconsets/v5/search"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Saving images to: {OUTPUT_DIR}")

    if API_KEY == "YOUR_ICONS8_API_KEY_HERE":
        print("ERROR: Set your Icons8 API_KEY in the script before running.")
        return

    for product_id, query in products.items():
        params = {"term": query, "amount": 1, "platform": STYLE, "token": API_KEY}
        try:
            resp = requests.get(SEARCH_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("icons"):
                print(f"  No results for: {product_id} ('{query}')")
                continue
            icon_id = data["icons"][0]["id"]
            img_url = f"https://img.icons8.com/{STYLE}/{SIZE}/{icon_id}.png"
            img_resp = requests.get(img_url, timeout=15)
            img_resp.raise_for_status()
            filepath = os.path.join(OUTPUT_DIR, f"{product_id}.png")
            with open(filepath, "wb") as f:
                f.write(img_resp.content)
            print(f"  OK: {product_id}.png <- '{query}'")
        except Exception as e:
            print(f"  FAIL: {product_id} ('{query}'): {e}")


if __name__ == "__main__":
    main()
