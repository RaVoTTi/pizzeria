/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        const order = this.pos.getOrder();
        if (order) {
            order.is_takeaway = order.order_type === 'retira' || order.order_type === 'delivery';
            order.is_dine_in = order.order_type === 'mesa' || (!order.order_type && !!order.table_id);
        }
    },

    get buttonClass() {
        const order = this.pos.getOrder();
        if (order && (order.order_type === 'retira' || order.order_type === 'delivery' || order.is_takeaway)) {
            return "control-button customer-button btn rounded-0 fw-bolder text-truncate btn-primary";
        }
        return "control-button btn btn-light rounded-0 fw-bolder";
    },

    async onClick() {
        const SelectedOrder = this.pos.getOrder();
        if (SelectedOrder.is_empty()) {
            return alert('Please add product!!');
        }

        if (SelectedOrder.is_takeaway || SelectedOrder.order_type === 'retira' || SelectedOrder.order_type === 'delivery') {
            SelectedOrder.is_dine_in = true;
            SelectedOrder.is_takeaway = false;
            SelectedOrder.order_type = 'mesa';
            if (this.pos.config.is_generate_token) {
                this.pos.config.pos_token -= 1;
            }
        } else {
            SelectedOrder.is_takeaway = true;
            SelectedOrder.is_dine_in = false;
            SelectedOrder.order_type = 'retira';
            SelectedOrder.generate_token = true;
            if (this.pos.config.is_generate_token) {
                this.pos.config.pos_token += 1;
            }
        }
    }
});