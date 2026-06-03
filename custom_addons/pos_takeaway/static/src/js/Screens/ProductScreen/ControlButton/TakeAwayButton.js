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
            order.is_takeaway = order.is_takeaway || false;
            order.is_dine_in = order.is_dine_in !== false;
        }
    },

    get buttonClass() {
        const order = this.pos.getOrder();
        if (order && order.is_takeaway) {
            return "control-button customer-button btn rounded-0 fw-bolder text-truncate btn-primary";
        }
        return "control-button btn btn-light rounded-0 fw-bolder";
    },

    async onClick() {
        const SelectedOrder = this.pos.getOrder();
        if (SelectedOrder.is_empty()) {
            return alert('Please add product!!');
        }

        if (SelectedOrder.is_takeaway) {
            SelectedOrder.is_dine_in = true;
            SelectedOrder.is_takeaway = false;
            if (this.pos.config.is_generate_token) {
                this.pos.config.pos_token -= 1;
            }
        } else {
            SelectedOrder.is_takeaway = true;
            SelectedOrder.is_dine_in = false;
            SelectedOrder.generate_token = true;
            if (this.pos.config.is_generate_token) {
                this.pos.config.pos_token += 1;
            }
        }
    }
});
