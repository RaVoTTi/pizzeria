/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    async printKitchenTicket() {
        const order = this.currentOrder;
        console.log("[Thermal Print] Order:", order);
        console.log("[Thermal Print] Order ID:", order?.id);
        console.log("[Thermal Print] Server ID:", order?.server_id);
        console.log("[Thermal Print] Order name:", order?.name);
        console.log("[Thermal Print] Order lines:", order?.lines?.length);
        
        if (!order) {
            console.error("[Thermal Print] No order found");
            this.notification.add("No hay pedido activo", { type: "danger" });
            return;
        }
        
        if (!order.server_id) {
            console.warn("[Thermal Print] Order not synced to server yet");
            console.log("[Thermal Print] Attempting to sync order...");
            try {
                await this.pos.syncAllOrders();
                console.log("[Thermal Print] Sync completed, server_id:", order.server_id);
            } catch (syncError) {
                console.error("[Thermal Print] Sync failed:", syncError);
                this.notification.add("Error al sincronizar pedido", { type: "danger" });
                return;
            }
        }
        
        if (!order.server_id) {
            console.error("[Thermal Print] Still no server_id after sync");
            this.notification.add("Pedido no sincronizado con el servidor", { type: "warning" });
            return;
        }
        
        console.log("[Thermal Print] Calling print_thermal_receipt with server_id:", order.server_id);
        try {
            const result = await this.orm.call(
                "pos.order",
                "print_thermal_receipt",
                [[order.server_id]]
            );
            console.log("[Thermal Print] Server response:", result);
            if (result) {
                this.notification.add("Ticket enviado a impresora", { type: "success" });
            } else {
                this.notification.add("Error al imprimir ticket", { type: "danger" });
            }
        } catch (error) {
            console.error("[Thermal Print] RPC error:", error);
            console.error("[Thermal Print] Error details:", error.message);
            this.notification.add(`Error: ${error.message}`, { type: "danger" });
        }
    },
});
