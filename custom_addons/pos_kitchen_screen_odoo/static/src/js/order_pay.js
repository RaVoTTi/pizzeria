/** @odoo-module **/
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async _finalizeValidation() {
        return super._finalizeValidation(...arguments);
    },
});
