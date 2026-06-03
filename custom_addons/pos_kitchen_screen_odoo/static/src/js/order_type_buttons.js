/** @odoo-module */
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    get currentOrderType() {
        const order = this.pos.getOrder();
        return order?.order_type || null;
    },

    get mesaClass() {
        return this.currentOrderType === 'mesa'
            ? 'control-button btn btn-primary rounded-0 fw-bolder'
            : 'control-button btn btn-light rounded-0 fw-bolder';
    },

    get deliveryClass() {
        return this.currentOrderType === 'delivery'
            ? 'control-button btn btn-warning rounded-0 fw-bolder'
            : 'control-button btn btn-light rounded-0 fw-bolder';
    },

    get retiraClass() {
        return this.currentOrderType === 'retira'
            ? 'control-button btn btn-secondary rounded-0 fw-bolder'
            : 'control-button btn btn-light rounded-0 fw-bolder';
    },

    setOrderType(type) {
        const order = this.pos.getOrder();
        if (order) {
            order.order_type = type;
        }
    },
});
