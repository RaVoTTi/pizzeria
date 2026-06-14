/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.doThermalPrint = useTrackedAsync(() => this._printThermalReceipt());
    },

    async _printThermalReceipt() {
        const order = this.currentOrder;
        if (!order) {
            return;
        }
        await this.pos.data.call("pos.order", "print_thermal_receipt", [[order.id]]);
        this.notification.add("Ticket enviado a impresora", { type: "info" });
    },
});
