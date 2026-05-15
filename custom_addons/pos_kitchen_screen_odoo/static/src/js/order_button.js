/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { useService } from "@web/core/utils/hooks";

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    async processOrderForKitchen() {
        const order = this.pos.getOrder();
        if (!order) {
            return;
        }

        const orderData = {
            pos_reference: order.pos_reference,
            config_id: order.config_id.id,
            table_id: order.table_id?.id || false,
            session_id: order.session_id.id,
        };

        await this.pos.syncAllOrders();
        await this.orm.call("pos.order", "process_order_for_kitchen", [orderData]);
    },
});
