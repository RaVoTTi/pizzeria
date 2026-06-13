/** @odoo-module */
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(PosStore.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    async printReceipt(options = {}) {
        const result = await super.printReceipt(...arguments);
        const order = options.order || this.getOrder();
        if (order && order.server_id) {
            try {
                await this.orm.call("pos.order", "print_customer_receipt", [order.server_id]);
                this.notification.add("Ticket enviado a impresora", { type: "info" });
            } catch (error) {
                console.error("Error printing to thermal printer:", error);
            }
        }
        return result;
    },
});
