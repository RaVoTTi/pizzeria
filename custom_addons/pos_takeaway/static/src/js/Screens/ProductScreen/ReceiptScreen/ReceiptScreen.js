import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        return {
            ...super.getReceiptHeaderData(...arguments),
            takeaway: order.is_takeaway,
            DineIn: order.is_dine_in,
            token_number : this.config.pos_token,
        };
    },
});
