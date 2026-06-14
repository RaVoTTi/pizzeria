/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    getStatus(order) {
        if (order.finalized) {
            return "PAGADO";
        }
        const screen = order.getScreenData();
        const screenName = screen?.name;

        if (screenName === "ProductScreen") {
            return "FALTA PAGAR";
        }
        if (screenName === "PaymentScreen") {
            return "NO PAGO";
        }
        if (screenName === "ReceiptScreen") {
            return "NO PAGO";
        }
        return "FALTA PAGAR";
    },

    getBadgeColorClass(order) {
        if (order.finalized) {
            return "badge rounded fs-6 text-bg-success";
        }
        const screen = order.getScreenData();
        const screenName = screen?.name;

        if (screenName === "PaymentScreen" || screenName === "ReceiptScreen") {
            return "badge rounded fs-6 text-bg-danger";
        }
        return "badge rounded fs-6";
    },

    getBadgeStyle(order) {
        if (order.finalized) {
            return "";
        }
        const screen = order.getScreenData();
        const screenName = screen?.name;

        if (screenName === "PaymentScreen" || screenName === "ReceiptScreen") {
            return "";
        }
        return "background-color: #8B0000; color: white;";
    },
});
