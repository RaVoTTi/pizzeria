/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

const MITAD_PRODUCT_NAME = "Mitad y Mitad";

function findPizzaPrice(posModels, pizzaName) {
    const products = posModels["product.product"].getAll();
    for (const p of products) {
        const name = (p.display_name || p.name || "").trim();
        if (name === pizzaName) {
            return p.lst_price || 0;
        }
    }
    for (const p of products) {
        const name = (p.display_name || p.name || "").trim();
        if (name.startsWith(pizzaName)) {
            return p.lst_price || 0;
        }
    }
    return 0;
}

patch(PosStore.prototype, {
    handlePriceUnit(values, order, price_unit) {
        const productTmpl = values.product_tmpl_id;
        const isMitad =
            productTmpl &&
            (productTmpl.display_name || productTmpl.name || "").includes(MITAD_PRODUCT_NAME);

        if (!isMitad) {
            return super.handlePriceUnit(...arguments);
        }

        if (price_unit !== undefined) {
            return super.handlePriceUnit(...arguments);
        }

        const ptavs = values.attribute_value_ids || [];
        let ladoA = null;
        let ladoB = null;

        for (const [cmd, ptav] of ptavs) {
            const attrName = ptav.attribute_id?.name || "";
            const valName = ptav.product_attribute_value_id?.name || ptav.name || "";
            if (attrName.includes("Lado A")) {
                ladoA = valName;
            } else if (attrName.includes("Lado B")) {
                ladoB = valName;
            }
        }

        if (ladoA && ladoB) {
            const priceA = findPizzaPrice(this.data.models, ladoA);
            const priceB = findPizzaPrice(this.data.models, ladoB);
            const maxPrice = Math.max(priceA, priceB);
            if (maxPrice > 0) {
                values.price_unit = maxPrice;
                values.price_type = "manual";
                values.price_extra = 0;
                return;
            }
        }

        return super.handlePriceUnit(...arguments);
    },
});