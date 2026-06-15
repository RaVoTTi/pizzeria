/** @odoo-module */
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
const { Component, onMounted, onWillUnmount, useState } = owl;
import { useService } from "@web/core/utils/hooks";

const UNDO_WINDOW_MS = 5000;
const GHOST_DURATION_MS = 10000;
const OVEN_CAPACITY = 6;
const SLA_WARNING_MIN = 30;
const SLA_AMBER_MIN = 10;

class KitchenScreenDashboard extends Component {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.busService = useService("bus_service");
        this.notification = useService("notification");

        this.loadTickets = this.loadTickets.bind(this);
        this.onTicketNotification = this.onTicketNotification.bind(this);
        this.onCardClick = this.onCardClick.bind(this);
        this.cancelTicket = this.cancelTicket.bind(this);
        this.printTicket = this.printTicket.bind(this);
        this.onLineClick = this.onLineClick.bind(this);
        this.cancelLine = this.cancelLine.bind(this);
        this.getElapsedMinutes = this.getElapsedMinutes.bind(this);
        this.getElapsedColor = this.getElapsedColor.bind(this);
        this.getTicketType = this.getTicketType.bind(this);
        this.getPartnerName = this.getPartnerName.bind(this);
        this.formatRequestedTime = this.formatRequestedTime.bind(this);
        this.formatTimeDisplay = this.formatTimeDisplay.bind(this);
        this.getLineStatusLabel = this.getLineStatusLabel.bind(this);
        this.getRemainingQty = this.getRemainingQty.bind(this);
        this.getPaymentStatusLabel = this.getPaymentStatusLabel.bind(this);
        this.togglePrepHeader = this.togglePrepHeader.bind(this);
        this.setStation = this.setStation.bind(this);
        this.undoLastAction = this.undoLastAction.bind(this);
        this.dismissAudioAlert = this.dismissAudioAlert.bind(this);
        this.getModifierClass = this.getModifierClass.bind(this);
        this.getCardClasses = this.getCardClasses.bind(this);
        this.acknowledgeModification = this.acknowledgeModification.bind(this);

        this.pendingStage = () => { this.state.stages = 'pending'; };
        this.cookingStage = () => { this.state.stages = 'cooking'; };
        this.readyStage = () => { this.state.stages = 'ready'; };
        this.deliveredStage = () => { this.state.stages = 'delivered'; };

        this.currentShopId = this.getCurrentShopId();
        // Channel must match KITCHEN_BUS_CHANNEL in models/pos_kitchen_sync.py
        // If these drift apart, real-time push silently breaks.
        this.channel = `pos_kitchen.${this.currentShopId}`;

        this.state = useState({
            tickets: [],
            sortedTickets: [],
            shop_id: this.currentShopId,
            stages: 'pending',
            pending_count: 0,
            cooking_count: 0,
            ready_count: 0,
            delivered_count: 0,
            isLoading: false,
            prepExpanded: false,
            prepSummary: [],
            stations: [],
            activeStation: 'all',
            showOvenQueue: true,
            ovenCapacity: OVEN_CAPACITY,
            ovenAvailable: OVEN_CAPACITY,
            ovenWaiting: 0,
            undoToast: {
                visible: false,
                message: '',
                action: null,
                progress: 100,
                duration: UNDO_WINDOW_MS,
            },
            audioAlertActive: false,
            ghostingTickets: new Set(),
        });

        this._undoTimeout = null;
        this._audioCtx = null;

        onMounted(() => {
            console.log("[KDS] onMounted: subscribing to bus channel", this.channel, "for shop", this.currentShopId);
            this.busService.addChannel(this.channel);
            this.busService.subscribe('notification', this.onTicketNotification);
            this.loadTickets();

            this._unlockAudio = () => {
                if (this._audioCtx && this._audioCtx.state === 'suspended') {
                    this._audioCtx.resume();
                }
            };
            document.addEventListener('click', this._unlockAudio, { once: true });

            this.autoRefreshInterval = setInterval(() => {
                this.loadTickets();
            }, 30000);

            this.elapsedTimer = setInterval(() => {
                this._recomputeDerived();
            }, 60000);
        });

        onWillUnmount(() => {
            this.busService.deleteChannel(this.channel);
            this.busService.unsubscribe('notification', this.onTicketNotification);
            clearInterval(this.autoRefreshInterval);
            clearInterval(this.elapsedTimer);
            if (this._undoTimeout) clearTimeout(this._undoTimeout);
            document.removeEventListener('click', this._unlockAudio);
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
        if (m < SLA_AMBER_MIN) return 'green';
        if (m <= SLA_WARNING_MIN) return 'amber';
        return 'red';
    }

    getTicketType(ticket) {
        return ticket.order_type || 'mesa';
    }

    getPartnerName(ticket) {
        return ticket.partner_name || '';
    }

    formatRequestedTime(ticket) {
        if (!ticket.requested_time) return '';
        const d = typeof ticket.requested_time === 'string'
            ? new Date(ticket.requested_time.replace(' ', 'T') + 'Z')
            : new Date(ticket.requested_time);
        if (isNaN(d.getTime())) return ticket.requested_time;
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    formatTimeDisplay(ticket) {
        const mins = this.getElapsedMinutes(ticket);
        const requested = this.formatRequestedTime(ticket);
        if (requested) {
            return { text: `${mins} MIN · ${requested}`, hasRequested: true };
        }
        return { text: `${mins} MIN`, hasRequested: false };
    }

    getLineStatusLabel(state) {
        const labels = {
            pending: _t('Pend'),
            cooking: _t('Horno'),
            ready: _t('Listo'),
            cancelled: _t('X'),
        };
        return labels[state] || state;
    }

    getRemainingQty(line) {
        return (line.qty_total || 0) - (line.qty_cancelled || 0);
    }

    getPaymentStatusLabel(status) {
        return status === 'paid' ? _t('PAGADO') : _t('FALTA PAGAR');
    }

    getModifierClass(note) {
        const n = (note || '').toLowerCase();
        if (n.startsWith('sin ') || n.startsWith('no ')) return 'kds-inline-note--sin';
        if (n.startsWith('extra ') || n.startsWith('con extra') || n.startsWith('mas ')) return 'kds-inline-note--extra';
        return '';
    }

    getCardClasses(ticket) {
        const classes = [`kds-card`];
        if (ticket.state) classes.push(`kds-card[data-state="${ticket.state}"]`);
        if (ticket.isNew) classes.push('kds-card--new');
        if (this.getElapsedMinutes(ticket) >= SLA_WARNING_MIN && ticket.state === 'pending') {
            classes.push('kds-card--sla-warning');
        }
        if (ticket.syncError) classes.push('kds-card--sync-error');
        if (this.state.ghostingTickets.has(ticket.id)) classes.push('kds-card--ghosting');
        if (ticket.optimistic) classes.push('kds-card--optimistic');
        return classes.join(' ');
    }

    togglePrepHeader() {
        this.state.prepExpanded = !this.state.prepExpanded;
    }

    setStation(stationId) {
        this.state.activeStation = stationId;
        this._recomputeDerived();
    }

    dismissAudioAlert() {
        this.state.audioAlertActive = false;
    }

    _playChime() {
        try {
            if (!this._audioCtx) {
                this._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            const ctx = this._audioCtx;
            if (ctx.state === 'suspended') {
                ctx.resume();
            }
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = 880;
            osc.type = 'sine';
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.5);
        } catch (e) {
        }
    }

    _vibrate(pattern = [100, 50, 100]) {
        try {
            if (navigator.vibrate) {
                navigator.vibrate(pattern);
            }
        } catch (e) {
        }
    }

    _showUndoToast(message, action) {
        this.state.undoToast = {
            visible: true,
            message,
            action,
            progress: 100,
            duration: UNDO_WINDOW_MS,
        };

        if (this._undoTimeout) clearTimeout(this._undoTimeout);
        this._undoTimeout = setTimeout(() => {
            this.state.undoToast.visible = false;
            this.state.undoToast.action = null;
        }, UNDO_WINDOW_MS);
    }

    async undoLastAction() {
        if (!this.state.undoToast.action) return;
        const action = this.state.undoToast.action;
        try {
            await action.undo();
            this.notification.add(_t('Accion deshecha'), { type: 'info' });
        } catch (e) {
            this.notification.add(_t('Error al deshacer'), { type: 'danger' });
        }
        this.state.undoToast.visible = false;
        this.state.undoToast.action = null;
        if (this._undoTimeout) clearTimeout(this._undoTimeout);
    }

    async loadTickets() {
        if (this.state.isLoading) return;
        try {
            this.state.isLoading = true;
            console.log("[KDS] loadTickets: fetching for shop", this.currentShopId);
            const result = await this.orm.call("pos.kitchen.ticket", "get_details", [this.currentShopId]);
            const tickets = result.tickets || [];
            const stations = result.stations || [];
            
            const newIds = new Set(tickets.map(t => t.id));
            const oldIds = new Set(this.state.tickets.map(t => t.id));
            const hasNewTickets = [...newIds].some(id => !oldIds.has(id));

            console.log("[KDS] loadTickets: received", tickets.length, "tickets, hasNewTickets:", hasNewTickets);
            tickets.forEach(t => {
                console.log("[KDS]   ticket id=" + t.id + " seq=" + t.sequence + t.batch_letter + " state=" + t.state + " type=" + t.ticket_type + " lines=" + (t.lines ? t.lines.length : 0));
                if (t.lines) {
                    t.lines.forEach(l => {
                        console.log("[KDS]     line id=" + l.id + " product=" + l.full_product_name + " qty=" + l.qty_total + " state=" + l.state + " note=" + l.note + " modified=" + l.modified);
                    });
                }
            });

            this.state.tickets = tickets;
            this.state.stations = stations;
            this._recomputeDerived();

            if (hasNewTickets) {
                this.state.audioAlertActive = true;
                this._playChime();
                this._vibrate([100, 50, 100]);
            }
        } catch (error) {
            console.error("Error loading tickets:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    _recomputeDerived() {
        const filtered = this._filterByStation(this.state.tickets);
        this.state.sortedTickets = this._sortByAge(filtered);
        this.state.pending_count = this.state.sortedTickets.filter(t => t.state === 'pending').length;
        this.state.cooking_count = this.state.sortedTickets.filter(t => t.state === 'cooking').length;
        this.state.ready_count = this.state.sortedTickets.filter(t => t.state === 'ready').length;
        this.state.delivered_count = this.state.sortedTickets.filter(t => t.state === 'delivered').length;
        this.state.prepSummary = this._computePrepSummary(this.state.sortedTickets);
        this._computeOvenQueue();
    }

    _filterByStation(tickets) {
        if (this.state.activeStation === 'all') return tickets;
        return tickets.filter(t => {
            if (!t.lines) return false;
            return t.lines.some(l => {
                const cat = l.product_category || '';
                return cat === this.state.activeStation;
            });
        });
    }

    _sortByAge(tickets) {
        return [...tickets].sort((a, b) => {
            const da = a.date_order ? new Date(a.date_order.replace(' ', 'T')) : new Date(0);
            const db = b.date_order ? new Date(b.date_order.replace(' ', 'T')) : new Date(0);
            return da - db;
        });
    }

    _computePrepSummary(tickets) {
        const active = tickets.filter(t => !['delivered', 'cancelled'].includes(t.state));
        const counts = {};
        active.forEach(t => {
            (t.lines || []).forEach(l => {
                if (l.state === 'cancelled') return;
                const key = l.product_id || l.full_product_name;
                if (!counts[key]) {
                    counts[key] = {
                        product_id: key,
                        name: l.full_product_name || key,
                        qty: 0,
                        isUrgent: false,
                    };
                }
                counts[key].qty += l.qty_total || 1;
                if (this.getElapsedMinutes(t) >= SLA_WARNING_MIN) {
                    counts[key].isUrgent = true;
                }
            });
        });
        return Object.values(counts).sort((a, b) => b.qty - a.qty);
    }

    _computeOvenQueue() {
        const cookingTickets = this.state.sortedTickets.filter(t => t.state === 'cooking');
        let totalPizzas = 0;
        cookingTickets.forEach(t => {
            (t.lines || []).forEach(l => {
                const cat = (l.product_category || '').toLowerCase();
                if (cat.includes('pizza') || cat.includes('empanada')) {
                    totalPizzas += l.qty_total || 1;
                }
            });
        });
        this.state.ovenAvailable = Math.max(0, this.state.ovenCapacity - totalPizzas);
    }

    onTicketNotification(message) {
        console.log("[KDS] onTicketNotification received:", JSON.stringify(message));
        if (!message || message.config_id !== this.currentShopId) {
            console.log("[KDS] onTicketNotification: ignoring (config mismatch or null). my shop=" + this.currentShopId + " msg config=" + (message ? message.config_id : 'null'));
            return;
        }
        const relevant = [
            'pos_order_created', 'pos_order_updated', 'pos_order_paid',
            'pos_order_accepted', 'pos_order_cancelled', 'pos_order_completed',
            'pos_order_delivered', 'pos_order_line_updated',
            'pos_order_line_cooking', 'pos_order_line_ready', 'pos_order_line_cancelled',
            'pos_order_line_modified', 'pos_order_line_acknowledged',
        ];
        if (!relevant.includes(message.message)) return;

        if (message.order_id) {
            this._reloadOrderTickets(message.order_id);
        } else {
            this.loadTickets();
        }
    }

    async _reloadOrderTickets(orderId) {
        console.log("[KDS] _reloadOrderTickets: targeting order", orderId);
        try {
            const result = await this.orm.call("pos.kitchen.ticket", "get_details_for_order", [this.currentShopId, orderId]);
            const freshTickets = result.tickets || [];
            console.log("[KDS] _reloadOrderTickets: received", freshTickets.length, "tickets for order", orderId);

            const otherTickets = this.state.tickets.filter(
                t => t.origin_pos_order_id !== orderId
            );
            this.state.tickets = [...otherTickets, ...freshTickets];
            this._recomputeDerived();
        } catch (error) {
            console.error("[KDS] _reloadOrderTickets: error, falling back to full reload:", error);
            this.loadTickets();
        }
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

        const prevState = ticket.state;
        ticket.state = next;
        ticket.optimistic = true;
        ticket.syncError = false;
        this.state.tickets = [...this.state.tickets];
        this._recomputeDerived();

        const method = next === 'cooking' ? 'progress_to_cooking'
            : next === 'ready' ? 'progress_to_ready'
            : 'progress_to_delivered';

        const undoAction = () => {
            ticket.state = prevState;
            ticket.optimistic = false;
            this.state.tickets = [...this.state.tickets];
            this._recomputeDerived();
            return this.orm.call("pos.kitchen.ticket", this._reverseMethod(method), [ticket.id]);
        };

        this.orm.call("pos.kitchen.ticket", method, [ticket.id])
            .then(() => {
                ticket.optimistic = false;
                this.state.tickets = [...this.state.tickets];
            })
            .catch(err => {
                ticket.syncError = true;
                ticket.state = prevState;
                this.state.tickets = [...this.state.tickets];
                this._recomputeDerived();
                console.error("Error advancing ticket:", err);
            });

        const actionLabel = next === 'cooking' ? _t('al Horno')
            : next === 'ready' ? _t('Listo')
            : next === 'delivered' ? 'Delivery'
            : next;
        this._showUndoToast(_t(`Ticket movido a ${actionLabel}`), { undo: undoAction });

        if (next === 'delivered') {
            setTimeout(() => {
                this.state.ghostingTickets.add(ticket.id);
                this.state.tickets = [...this.state.tickets];
                setTimeout(() => {
                    this.state.ghostingTickets.delete(ticket.id);
                    this.loadTickets();
                }, GHOST_DURATION_MS);
            }, 2000);
        }
    }

    _reverseMethod(method) {
        const reverse = {
            progress_to_cooking: 'cancel_ticket',
            progress_to_ready: 'progress_to_cooking',
            progress_to_delivered: 'progress_to_ready',
        };
        return reverse[method] || 'cancel_ticket';
    }

    async printTicket(ev, ticket) {
        ev.stopPropagation();
        try {
            await this.orm.call("pos.kitchen.ticket", "print_ticket", [ticket.id]);
            this.notification.add(_t("Ticket enviado a impresora"), { type: "info" });
        } catch (error) {
            this.notification.add(_t("Error al imprimir ticket"), { type: "danger" });
            console.error("Error printing ticket:", error);
        }
    }

    async cancelTicket(e) {
        const ticketId = Number(e.target.value);
        const ticket = this.state.tickets.find(t => t.id === ticketId);
        if (!ticket) return;

        const prevState = ticket.state;
        const prevPaymentStatus = ticket.payment_status;
        ticket.state = 'cancelled';
        this.state.tickets = [...this.state.tickets];
        this._recomputeDerived();

        const undoAction = () => {
            ticket.state = prevState;
            ticket.payment_status = prevPaymentStatus;
            this.state.tickets = [...this.state.tickets];
            this._recomputeDerived();
            return Promise.resolve();
        };

        try {
            await this.orm.call("pos.kitchen.ticket", "cancel_ticket", [ticketId]);
            this._showUndoToast(_t(`Ticket cancelado`), { undo: undoAction });
        } catch (error) {
            ticket.state = prevState;
            ticket.payment_status = prevPaymentStatus;
            this.state.tickets = [...this.state.tickets];
            this._recomputeDerived();
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

        const prevState = line.state;
        line.state = next;
        this.state.tickets = [...this.state.tickets];
        this._recomputeDerived();

        try {
            await this.orm.call("pos.kitchen.ticket.line", method, [line.id]);
        } catch (error) {
            line.state = prevState;
            this.state.tickets = [...this.state.tickets];
            this._recomputeDerived();
            console.error("Error updating line:", error);
        }
    }

    async cancelLine(ev, line) {
        ev.stopPropagation();
        const prevState = line.state;
        line.state = 'cancelled';
        this.state.tickets = [...this.state.tickets];
        this._recomputeDerived();

        try {
            await this.orm.call("pos.kitchen.ticket.line", "action_cancel", [line.id]);
        } catch (error) {
            line.state = prevState;
            this.state.tickets = [...this.state.tickets];
            this._recomputeDerived();
            console.error("Error cancelling line:", error);
        }
    }

    async acknowledgeModification(ev, line) {
        ev.stopPropagation();
        try {
            await this.orm.call("pos.kitchen.ticket.line", "acknowledge_modification", [line.id]);
        } catch (error) {
            console.error("Error acknowledging modification:", error);
        }
    }
}

KitchenScreenDashboard.template = 'KitchenCustomDashBoard';
registry.category("actions").add("kitchen_custom_dashboard_tags", KitchenScreenDashboard);
