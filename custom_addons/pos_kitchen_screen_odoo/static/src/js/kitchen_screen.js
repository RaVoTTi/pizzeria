/** @odoo-module */
import { registry } from "@web/core/registry";
const { Component, onMounted, onWillUnmount, useState } = owl;
import { useService } from "@web/core/utils/hooks";

class KitchenScreenDashboard extends Component {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.busService = useService("bus_service");

        this.loadOrders = this.loadOrders.bind(this);
        this.onPosOrderCreation = this.onPosOrderCreation.bind(this);
        this.onCardClick = this.onCardClick.bind(this);
        this.cancelOrder = this.cancelOrder.bind(this);
        this.toggleOrderLine = this.toggleOrderLine.bind(this);
        this.getElapsedMinutes = this.getElapsedMinutes.bind(this);
        this.getElapsedColor = this.getElapsedColor.bind(this);
        this.getOrderType = this.getOrderType.bind(this);
        this.getCustomerName = this.getCustomerName.bind(this);

        this.draftStage = () => { this.state.stages = 'draft'; };
        this.waitingStage = () => { this.state.stages = 'waiting'; };
        this.readyStage = () => { this.state.stages = 'ready'; };
        this.deliveredStage = () => { this.state.stages = 'delivered'; };

        this.currentShopId = this.getCurrentShopId();
        this.channel = `pos_order_created_${this.currentShopId}`;

        this.state = useState({
            order_details: [],
            shop_id: this.currentShopId,
            stages: 'draft',
            draft_count: 0,
            waiting_count: 0,
            ready_count: 0,
            delivered_count: 0,
            lines: [],
            isLoading: false,
        });

        onMounted(() => {
            this.busService.addChannel(this.channel);
            this.busService.subscribe('notification', this.onPosOrderCreation);
            this.loadOrders();

            this.autoRefreshInterval = setInterval(() => {
                this.loadOrders();
            }, 30000);

            this.elapsedTimer = setInterval(() => {
                this.state.order_details = [...this.state.order_details];
            }, 60000);
        });

        onWillUnmount(() => {
            this.busService.deleteChannel(this.channel);
            this.busService.unsubscribe('notification', this.onPosOrderCreation);
            clearInterval(this.autoRefreshInterval);
            clearInterval(this.elapsedTimer);
        });
    }

    getCurrentShopId() {
        let shopId;
        if (this.props.action?.context?.default_shop_id) {
            sessionStorage.setItem('shop_id', this.props.action.context.default_shop_id);
            shopId = this.props.action.context.default_shop_id;
        } else {
            shopId = sessionStorage.getItem('shop_id');
        }
        return parseInt(shopId, 10) || 0;
    }

    getElapsedMinutes(order) {
        if (!order.date_order) return 0;
        const orderDate = typeof order.date_order === 'string'
            ? new Date(order.date_order.replace(' ', 'T'))
            : new Date(order.date_order);
        return Math.max(0, Math.floor((Date.now() - orderDate) / 60000));
    }

    getElapsedColor(order) {
        const m = this.getElapsedMinutes(order);
        if (m < 10) return 'green';
        if (m <= 20) return 'amber';
        return 'red';
    }

    getOrderType(order) {
        return (order.table_id && Array.isArray(order.table_id) && order.table_id[0]) ? 'mesa' : 'delivery';
    }

    getCustomerName(order) {
        if (order.partner_id && Array.isArray(order.partner_id) && order.partner_id[1]) {
            return order.partner_id[1];
        }
        return '';
    }

    /* ---------- unified card click — advances to next state ---------- */
    onCardClick(ev, order) {
        ev.stopPropagation();
        this._advanceOrder(order);
    }

    _advanceOrder(order) {
        const id = order.id;

        // optimistic instant move
        const next = order.order_status === 'draft' ? 'waiting'
            : order.order_status === 'waiting' ? 'ready'
            : order.order_status === 'ready' ? 'delivered'
            : null;

        if (!next) return;

        order.order_status = next;
        this.state.order_details = [...this.state.order_details];

        // fire backend
        const method = next === 'waiting' ? 'order_progress_draft'
            : next === 'ready' ? 'order_progress_change'
            : 'order_progress_delivered';

        this.orm.call("pos.order", method, [id]).catch(err => {
            console.error("Error advancing order:", err);
        });

        setTimeout(() => this.loadOrders(), 1500);
    }

    async cancelOrder(e) {
        const orderId = Number(e.target.value);
        try {
            await this.orm.call("pos.order", "order_progress_cancel", [orderId]);
            const order = this.state.order_details.find(o => o.id === orderId);
            if (order) order.order_status = 'cancel';
            setTimeout(() => this.loadOrders(), 500);
        } catch (error) {
            console.error("Error cancelling order:", error);
        }
    }

    async toggleOrderLine(e) {
        const lineId = Number(e.target.value);
        try {
            await this.orm.call("pos.order.line", "order_progress_change", [lineId]);
            const line = this.state.lines.find(l => l.id === lineId);
            if (line) line.order_status = line.order_status === 'ready' ? 'waiting' : 'ready';
            setTimeout(() => this.loadOrders(), 500);
        } catch (error) {
            console.error("Error toggling order line:", error);
        }
    }

    async loadOrders() {
        if (this.state.isLoading) return;
        try {
            this.state.isLoading = true;
            const result = await this.orm.call("pos.order", "get_details", [this.currentShopId]);
            this.state.order_details = result.orders || [];
            this.state.lines = result.order_lines || [];

            const all = this.state.order_details.filter(o => {
                const cid = Array.isArray(o.config_id) ? o.config_id[0] : o.config_id;
                return cid === this.currentShopId;
            });

            this.state.draft_count = all.filter(o => o.order_status === 'draft').length;
            this.state.waiting_count = all.filter(o => o.order_status === 'waiting').length;
            this.state.ready_count = all.filter(o => o.order_status === 'ready').length;
            this.state.delivered_count = all.filter(o => o.order_status === 'delivered').length;
        } catch (error) {
            console.error("Error loading orders:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    onPosOrderCreation(message) {
        if (!message || message.config_id !== this.currentShopId) return;
        const msgs = ['pos_order_created','pos_order_updated','pos_order_paid','pos_order_accepted',
                      'pos_order_cancelled','pos_order_completed','pos_order_delivered','pos_order_line_updated'];
        if (msgs.includes(message.message)) this.loadOrders();
    }
}

KitchenScreenDashboard.template = 'KitchenCustomDashBoard';
registry.category("actions").add("kitchen_custom_dashboard_tags", KitchenScreenDashboard);