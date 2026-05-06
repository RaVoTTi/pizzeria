/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

export class MitadConfiguratorPopup extends Component {
    static template = "pos_mitad_configurator.MitadConfiguratorPopup";
    static components = { Dialog };

    setup() {
        this.pos = useService("pos");
        this.state = useState({
            step: 1,
            ladoA: null,
            ladoB: null,
            pizzas: [],
        });
        this.loadPizzas();
    }

    loadPizzas() {
        const product = this.props.product;
        const attrLines = product.attribute_line_ids || [];

        const ladoALine = attrLines.find(
            (l) => l.attribute_id && l.attribute_id.name === "Lado A"
        );
        const ladoBLine = attrLines.find(
            (l) => l.attribute_id && l.attribute_id.name === "Lado B"
        );

        if (!ladoALine || !ladoBLine) return;

        const pizzas = [];
        for (const val of ladoALine.value_ids || []) {
            const pizzaProduct = this.pos.models["product.product"].find(
                (p) => (p.display_name || p.name) === val.name && p.id !== product.id
            );
            pizzas.push({
                valueId: val.id,
                valueName: val.name,
                price: pizzaProduct ? pizzaProduct.lst_price : 0,
                hasImage: pizzaProduct && pizzaProduct.image_128,
                imageId: pizzaProduct ? pizzaProduct.id : null,
            });
        }
        this.state.pizzas = pizzas;
    }

    get title() {
        if (this.state.step === 1) {
            return "Selecciona la 1ra Mitad";
        }
        return this.state.ladoA
            ? this.state.ladoA.valueName + " + ?"
            : "Selecciona la 2da Mitad";
    }

    get finalPrice() {
        if (this.state.ladoA && this.state.ladoB) {
            return Math.max(this.state.ladoA.price, this.state.ladoB.price);
        }
        return this.props.product.lst_price || 0;
    }

    selectPizza(pizza) {
        if (this.state.step === 1) {
            this.state.ladoA = pizza;
            this.state.step = 2;
        } else if (this.state.step === 2 && this.state.ladoA.valueId !== pizza.valueId) {
            this.state.ladoB = pizza;
        }
    }

    back() {
        if (this.state.step === 2) {
            this.state.ladoB = null;
            this.state.step = 1;
        }
    }

    confirm() {
        if (!this.state.ladoA || !this.state.ladoB) return;
        this.props.confirm({
            ladoA: this.state.ladoA,
            ladoB: this.state.ladoB,
            price: this.finalPrice,
        });
    }

    cancel() {
        this.props.cancel();
    }
}

patch(ProductScreen.prototype, {
    async addProductToOrder(product) {
        const name = product.display_name || product.name || "";
        if (!name.includes("Mitad y Mitad")) {
            return this._super(product);
        }

        const { confirmed, payload } = await this.env.services.dialog.add(
            MitadConfiguratorPopup,
            { product }
        );

        if (!confirmed || !payload) return;

        const ptavIds = this._getMitadPtavIds(product, payload);
        if (ptavIds.length !== 2) return;

        await this.pos.addLineToCurrentOrder(
            {
                product_tmpl_id: product,
                price_unit: payload.price,
                payload: { attribute_value_ids: ptavIds },
            },
            {},
            true
        );

        const order = this.pos.get_order();
        const lines = order.get_orderlines();
        const lastLine = lines[lines.length - 1];
        if (lastLine && lastLine.set_note) {
            lastLine.set_note(
                "1/2 " + payload.ladoA.valueName + " + 1/2 " + payload.ladoB.valueName
            );
        }
    },

    _getMitadPtavIds(product, payload) {
        const ptavs = product.ptav_ids || product.product_template_attribute_value_ids || [];
        if (!ptavs.length) return [];
        const valAId = payload.ladoA.valueId;
        const valBId = payload.ladoB.valueId;
        return ptavs
            .filter((ptav) => {
                const pav = ptav.product_attribute_value_id;
                const pavId = typeof pav === "object" ? pav.id : pav;
                return pavId === valAId || pavId === valBId;
            })
            .map((ptav) => ptav.id);
    },
});
