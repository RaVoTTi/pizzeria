/** @odoo-module **/
import { Component, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.orm = useService("orm");
        this.TakeAway = useRef("TakeAway");
        this.pos.get_order().is_takeaway = false;
        this.pos.get_order().is_dine_in = true;
    },
    async onClick() {
        const SelectedOrder = this.pos.get_order();
        if (SelectedOrder.is_empty()) {
            return alert ('Please add product!!');
        }else{
            if (this.TakeAway.el.className === "control-button customer-button btn rounded-0 fw-bolder text-truncate btn-primary") {
                this.TakeAway.el.className = "control-button btn btn-light rounded-0 fw-bolder";
                SelectedOrder.is_dine_in = true;
                if (this.pos.config.is_generate_token) {
                    this.pos.config.pos_token -= 1;
                }
            }else{
                this.TakeAway.el.className = "control-button customer-button btn rounded-0 fw-bolder text-truncate btn-primary";
                if (this.pos.config.is_generate_token) {
                    this.pos.config.pos_token += 1;
                }
                SelectedOrder.is_takeaway = true;
                SelectedOrder.is_dine_in = false;
                SelectedOrder.generate_token = true;
            }
        }
    }
});
