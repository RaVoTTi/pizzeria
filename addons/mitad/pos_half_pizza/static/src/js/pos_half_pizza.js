/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

const MITAD_PRODUCT_NAME = "Mitad y Mitad";

function findPizzaPriceByName(pos, pizzaName) {
    const products = pos.models["product.product"];
    if (!products) return 0;
    for (const product of products) {
        const name = product.display_name || product.name || "";
        if (name === pizzaName && !name.includes(MITAD_PRODUCT_NAME)) {
            return product.lst_price || 0;
        }
    }
    for (const product of products) {
        const name = product.display_name || product.name || "";
        if (name.startsWith(pizzaName) && !name.includes(MITAD_PRODUCT_NAME)) {
            return product.lst_price || 0;
        }
    }
    return 0;
}

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        const line = await this._super(vals, order, opts, configure);
        if (!line) return line;

        const productTmpl = vals.product_tmpl_id;
        if (!productTmpl) return line;

        const name = productTmpl.display_name || productTmpl.name || "";
        if (!name.includes(MITAD_PRODUCT_NAME)) return line;

        const ptavs = line.product_template_attribute_value_ids || [];
        if (ptavs.length < 2) return line;

        let ladoA = null;
        let ladoB = null;
        for (const ptav of ptavs) {
            const attrName = ptav.attribute_id
                ? ptav.attribute_id[1] || ptav.attribute_id.name || ""
                : "";
            const valName = ptav.product_attribute_value_id
                ? ptav.product_attribute_value_id[1] ||
                  ptav.product_attribute_value_id.name ||
                  ""
                : "";

            if (attrName.includes("Lado A") || attrName === "Lado A") {
                ladoA = valName;
            } else if (attrName.includes("Lado B") || attrName === "Lado B") {
                ladoB = valName;
            }
        }

        if (!ladoA || !ladoB) return line;

        const priceA = findPizzaPriceByName(this.pos, ladoA);
        const priceB = findPizzaPriceByName(this.pos, ladoB);
        const maxPrice = Math.max(priceA, priceB);

        if (maxPrice > 0) {
            line.price_unit = maxPrice;
            line.price_type = "manual";
        }

        return line;
    },
});
