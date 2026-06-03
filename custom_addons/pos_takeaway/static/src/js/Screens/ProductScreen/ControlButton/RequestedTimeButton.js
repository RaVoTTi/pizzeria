/** @odoo-module */
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    get requestedTimeDisplay() {
        const order = this.pos.getOrder();
        if (!order?.requested_time) return '';
        const dt = order.requested_time;
        if (dt?.hour !== undefined) {
            return `${String(dt.hour).padStart(2, '0')}:${String(dt.minute).padStart(2, '0')}`;
        }
        if (typeof dt === 'string') {
            const match = dt.match(/(\d{2}):(\d{2})/);
            if (match) return `${match[1]}:${match[2]}`;
        }
        return '';
    },

    get requestedTimeClass() {
        const order = this.pos.getOrder();
        return order?.requested_time
            ? 'control-button btn btn-info rounded-0 fw-bolder'
            : 'control-button btn btn-light rounded-0 fw-bolder';
    },

    async setRequestedTime() {
        const order = this.pos.getOrder();
        if (!order) return;

        const currentTime = this.requestedTimeDisplay || '';
        const payload = await makeAwaitable(this.dialog, TextInputPopup, {
            title: 'Hora de entrega (HH:MM)',
            startingValue: currentTime,
            placeholder: 'Ej: 20:30',
        });

        if (payload && typeof payload === 'string') {
            const match = payload.match(/^(\d{1,2}):(\d{2})$/);
            if (match) {
                const hours = parseInt(match[1], 10);
                const minutes = parseInt(match[2], 10);
                if (hours >= 0 && hours <= 23 && minutes >= 0 && minutes <= 59) {
                    const now = new Date();
                    const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:00`;
                    order.requested_time = dateStr;
                } else {
                    alert('Hora inválida. Use formato HH:MM (00:00 - 23:59)');
                }
            } else if (payload.trim() === '') {
                order.requested_time = false;
            } else {
                alert('Formato inválido. Use HH:MM (ej: 20:30)');
            }
        }
    },
});
