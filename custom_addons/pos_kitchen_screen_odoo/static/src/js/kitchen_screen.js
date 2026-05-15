/** @odoo-module */
import { registry } from "@web/core/registry";
const { Component, onMounted, onWillUnmount, useState } = owl;
import { useService } from "@web/core/utils/hooks";

class KitchenScreenDashboard extends Component {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.busService = useService("bus_service");

        this.loadTickets = this.loadTickets.bind(this);
        this.onTicketNotification = this.onTicketNotification.bind(this);
        this.onCardClick = this.onCardClick.bind(this);
        this.cancelTicket = this.cancelTicket.bind(this);
        this.onLineClick = this.onLineClick.bind(this);
        this.cancelLine = this.cancelLine.bind(this);
        this.getElapsedMinutes = this.getElapsedMinutes.bind(this);
        this.getElapsedColor = this.getElapsedColor.bind(this);
        this.getTicketType = this.getTicketType.bind(this);
        this.getPartnerName = this.getPartnerName.bind(this);
        this.getTicketTypeLabel = this.getTicketTypeLabel.bind(this);
        this.getLineStatusLabel = this.getLineStatusLabel.bind(this);
        this.getRemainingQty = this.getRemainingQty.bind(this);

        this.pendingStage = () => { this.state.stages = 'pending'; };
        this.cookingStage = () => { this.state.stages = 'cooking'; };
        this.readyStage = () => { this.state.stages = 'ready'; };
        this.deliveredStage = () => { this.state.stages = 'delivered'; };
        
        this.getPaymentStatusLabel = this.getPaymentStatusLabel.bind(this);

        this.currentShopId = this.getCurrentShopId();
        this.channel = `pos_order_created_${this.currentShopId}`;

        this.state = useState({
            tickets: [],
            shop_id: this.currentShopId,
            stages: 'pending',
            pending_count: 0,
            cooking_count: 0,
            ready_count: 0,
            delivered_count: 0,
            isLoading: false,
        });

        onMounted(() => {
            this.busService.addChannel(this.channel);
            this.busService.subscribe('notification', this.onTicketNotification);
            this.loadTickets();

            this.autoRefreshInterval = setInterval(() => {
                this.loadTickets();
            }, 30000);

            this.elapsedTimer = setInterval(() => {
                this.state.tickets = [...this.state.tickets];
            }, 60000);
        });

        onWillUnmount(() => {
            this.busService.deleteChannel(this.channel);
            this.busService.unsubscribe('notification', this.onTicketNotification);
            clearInterval(this.autoRefreshInterval);
            clearInterval(this.elapsedTimer);
        });
    }

    getCurrentShopId() {
        let id;
        if (this.props.action?.context?.default_shop_id) {
            sessionStorage.setItem('shop_id', this.props.action.context.default_shop_id);
            id = this.props.action.context.default_shop_id;
        } else {
            id = sessionStorage.getItem('shop_id');
        }
        return parseInt(id, 10) || 0;
    }

    getElapsedMinutes(ticket) {
        if (!ticket.date_order) return 0;
        const d = typeof ticket.date_order === 'string'
            ? new Date(ticket.date_order.replace(' ', 'T'))
            : new Date(ticket.date_order);
        return Math.max(0, Math.floor((Date.now() - d) / 60000));
    }

    getElapsedColor(ticket) {
        const m = this.getElapsedMinutes(ticket);
        if (m < 10) return 'green';
        if (m <= 20) return 'amber';
        return 'red';
    }

    getTicketType(ticket) {
        return ticket.table_id ? 'mesa' : 'delivery';
    }

    getPartnerName(ticket) {
        return ticket.partner_name || '';
    }

    getTicketTypeLabel(type) {
        const labels = {
            new: 'NUEVO',
            addition: 'ADICION',
            cancellation: 'CANCEL',
            modification: 'MODIF',
        };
        return labels[type] || type;
    }

    getLineStatusLabel(state) {
        const labels = {
            pending: 'Pend',
            cooking: 'Horno',
            ready: 'Listo',
            cancelled: 'X',
        };
        return labels[state] || state;
    }

    getRemainingQty(line) {
        return (line.qty_total || 0) - (line.qty_cancelled || 0);
    }

    getPaymentStatusLabel(status) {
        return status === 'paid' ? 'PAGADO' : 'NO PAGADO';
    }

    async loadTickets() {
        if (this.state.isLoading) return;
        try {
            this.state.isLoading = true;
            const result = await this.orm.call("pos.kitchen.ticket", "get_details", [this.currentShopId]);
            this.state.tickets = result || [];
            this.state.pending_count = this.state.tickets.filter(t => t.state === 'pending').length;
            this.state.cooking_count = this.state.tickets.filter(t => t.state === 'cooking').length;
            this.state.ready_count = this.state.tickets.filter(t => t.state === 'ready').length;
            this.state.delivered_count = this.state.tickets.filter(t => t.state === 'delivered').length;
        } catch (error) {
            console.error("Error loading tickets:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    onTicketNotification(message) {
        if (!message || message.config_id !== this.currentShopId) return;
        const relevant = [
            'pos_order_created', 'pos_order_updated', 'pos_order_paid',
            'pos_order_accepted', 'pos_order_cancelled', 'pos_order_completed',
            'pos_order_delivered', 'pos_order_line_updated',
            'pos_order_line_cooking', 'pos_order_line_ready', 'pos_order_line_cancelled',
        ];
        if (relevant.includes(message.message)) this.loadTickets();
    }

    onCardClick(ev, ticket) {
        ev.stopPropagation();
        this._advanceTicket(ticket);
    }

    _advanceTicket(ticket) {
        const next = ticket.state === 'pending' ? 'cooking'
            : ticket.state === 'cooking' ? 'ready'
            : ticket.state === 'ready' ? 'delivered'
            : null;
        if (!next) return;

        ticket.state = next;
        this.state.tickets = [...this.state.tickets];

        const method = next === 'cooking' ? 'progress_to_cooking'
            : next === 'ready' ? 'progress_to_ready'
            : 'progress_to_delivered';

        this.orm.call("pos.kitchen.ticket", method, [ticket.id]).catch(err => {
            console.error("Error advancing ticket:", err);
        });

        setTimeout(() => this.loadTickets(), 1500);
    }

    async cancelTicket(e) {
        const ticketId = Number(e.target.value);
        try {
            await this.orm.call("pos.kitchen.ticket", "cancel_ticket", [ticketId]);
            const ticket = this.state.tickets.find(t => t.id === ticketId);
            if (ticket) ticket.state = 'cancelled';
            setTimeout(() => this.loadTickets(), 500);
        } catch (error) {
            console.error("Error cancelling ticket:", error);
        }
    }

    async onLineClick(ev, line) {
        ev.stopPropagation();
        const nextMap = {
            pending: 'cooking',
            cooking: 'ready',
            ready: 'cancelled',
            cancelled: 'pending',
        };
        const next = nextMap[line.state] || 'pending';

        const methodMap = {
            pending: 'action_cooking',
            cooking: 'action_ready',
            ready: 'action_cancel',
            cancelled: 'action_cooking',
        };
        const method = methodMap[line.state] || 'action_cooking';

        try {
            await this.orm.call("pos.kitchen.ticket.line", method, [line.id]);
            setTimeout(() => this.loadTickets(), 500);
        } catch (error) {
            console.error("Error updating line:", error);
        }
    }

    async cancelLine(ev, line) {
        ev.stopPropagation();
        try {
            await this.orm.call("pos.kitchen.ticket.line", "action_cancel", [line.id]);
            setTimeout(() => this.loadTickets(), 500);
        } catch (error) {
            console.error("Error cancelling line:", error);
        }
    }
}

KitchenScreenDashboard.template = 'KitchenCustomDashBoard';
registry.category("actions").add("kitchen_custom_dashboard_tags", KitchenScreenDashboard);
