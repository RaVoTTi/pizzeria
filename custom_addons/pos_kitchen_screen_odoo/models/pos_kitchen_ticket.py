# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _extract_note_text(note_value):
    """Extract text from Odoo 19 POS note field (JSON list of {text} dicts)."""
    if not note_value:
        return ""
    if isinstance(note_value, str):
        try:
            parsed = json.loads(note_value)
        except (json.JSONDecodeError, TypeError):
            return note_value.strip()
    else:
        parsed = note_value
    if isinstance(parsed, list):
        parts = [item.get("text", "") for item in parsed if isinstance(item, dict) and item.get("text")]
        return " ".join(parts)
    if isinstance(parsed, dict):
        return parsed.get("text", "")
    return str(parsed).strip()

VALID_TRANSITIONS = {
    "pending": {"cooking", "cancelled"},
    "cooking": {"ready", "cancelled"},
    "waiting": {"cooking", "cancelled"},
    "ready": {"delivered", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}

LINE_TRANSITIONS = {
    "pending": {"cooking"},
    "cooking": {"ready", "cancelled"},
    "waiting": {"cooking", "cancelled"},
    "ready": {"cancelled"},
    "cancelled": set(),
}


class PosKitchenTicket(models.Model):
    _name = "pos.kitchen.ticket"
    _description = "Kitchen Ticket"
    _order = "create_date desc"
    _rec_name = "sequence"

    origin_pos_order_id = fields.Many2one(
        "pos.order", string="Orden POS origen", required=True,
        ondelete="restrict", index=True)
    pos_config_id = fields.Many2one(
        "pos.config", related="origin_pos_order_id.config_id", store=True)
    pos_reference = fields.Char(
        related="origin_pos_order_id.pos_reference", store=True)
    order_name = fields.Char(
        related="origin_pos_order_id.name", store=True)
    table_id = fields.Many2one(
        "restaurant.table", related="origin_pos_order_id.table_id", store=True)
    partner_id = fields.Many2one(
        "res.partner", related="origin_pos_order_id.partner_id", store=True)
    session_id = fields.Many2one(
        "pos.session", related="origin_pos_order_id.session_id", store=True)

    sequence = fields.Char(
        readonly=True, default="Nuevo", copy=False)
    batch_letter = fields.Char(
        default="A", size=1,
        help="A=original, B/C/D=additions or cancellations")

    ticket_type = fields.Selection([
        ("new", "Nuevo"),
        ("addition", "Adicion"),
        ("cancellation", "Cancelacion"),
        ("modification", "Modificacion"),
    ], default="new", required=True, string="Tipo")

    state = fields.Selection([
        ("pending", "Pendiente"),
        ("cooking", "En Horno"),
        ("waiting", "Esperando Espacio"),
        ("ready", "Listo"),
        ("delivered", "Entregado"),
        ("cancelled", "Cancelado"),
    ], default="pending", string="Estado")

    payment_status = fields.Selection([
        ("paid", "Pagado"),
        ("not_paid", "No Pagado"),
    ], default="not_paid", string="Estado de Pago",
        help="Snapshot at ticket creation time")

    line_ids = fields.One2many(
        "pos.kitchen.ticket.line", "ticket_id", string="Lineas")

    started_at = fields.Datetime(string="Iniciado")
    ready_at = fields.Datetime(string="Listo a las")
    delivered_at = fields.Datetime(string="Entregado a las")
    requested_time = fields.Datetime(
        string="Hora solicitada",
        help="When the customer wants the order")

    def _notify_kitchen(self, message_type):
        self.ensure_one()
        msg = {
            "res_model": self._name,
            "message": message_type,
            "ticket_id": self.id,
            "config_id": self.pos_config_id.id,
        }
        channel = f"pos_kitchen.{self.pos_config_id.id}"
        self.env["bus.bus"]._sendone(channel, "notification", msg)

    def _transition(self, new_state):
        self.ensure_one()
        if new_state not in VALID_TRANSITIONS.get(self.state, set()):
            raise ValidationError(
                f"Cannot move ticket from '{self.state}' to '{new_state}'")
        self.state = new_state

    def _sync_state_from_lines(self):
        self.ensure_one()
        if not self.line_ids:
            return
        line_states = set(self.line_ids.mapped("state"))
        if line_states == {"ready"} or line_states == {"ready", "cancelled"}:
            if self.state != "ready":
                self.state = "ready"
                self.ready_at = fields.Datetime.now()
                self._notify_kitchen("pos_order_completed")
        elif line_states == {"cancelled"}:
            if self.state != "cancelled":
                self.state = "cancelled"
                self._notify_kitchen("pos_order_cancelled")
        elif "cooking" in line_states:
            if self.state == "pending":
                self.state = "cooking"
                self.started_at = self.started_at or fields.Datetime.now()
                self._notify_kitchen("pos_order_accepted")

    def progress_to_cooking(self):
        self.ensure_one()
        self._transition("cooking")
        self.started_at = fields.Datetime.now()
        self._notify_kitchen("pos_order_accepted")
        return True

    def progress_to_ready(self):
        self.ensure_one()
        self._transition("ready")
        self.ready_at = fields.Datetime.now()
        self.line_ids.write({"state": "ready"})
        self._notify_kitchen("pos_order_completed")

    def progress_to_delivered(self):
        self.ensure_one()
        self._transition("delivered")
        self.delivered_at = fields.Datetime.now()
        self._notify_kitchen("pos_order_delivered")

    def cancel_ticket(self):
        self.ensure_one()
        self._transition("cancelled")
        self.line_ids.write({"state": "cancelled"})
        self._notify_kitchen("pos_order_cancelled")

    def _get_oven_capacity(self):
        ks = self.env["kitchen.screen"].search(
            [("pos_config_id", "=", self.pos_config_id.id)], limit=1)
        return ks.oven_capacity if ks and ks.oven_capacity else 6

    def _count_oven_items(self):
        result = self.env["pos.kitchen.ticket.line"].read_group(
            [("ticket_id.pos_config_id", "=", self.pos_config_id.id),
             ("ticket_id.state", "=", "cooking"),
             ("product_category", "in", ["Pizza", "Empanada"])],
            ["qty_total:sum"],
            [],
        )
        return result[0]["qty_total"] if result and result[0]["qty_total"] else 0

    def _own_oven_items(self):
        count = 0
        for line in self.line_ids:
            cat = (line.product_category or "").lower()
            if "pizza" in cat or "empanada" in cat:
                count += line.qty_total
        return count

    def print_ticket(self, with_logo=True):
        self.ensure_one()
        return self.env["kitchen.ticket.printer"].print_ticket(self, with_logo=with_logo)

    def _get_product_category(self, product):
        return self.env["kitchen.ticket.printer"]._get_product_category(product)

    def action_line_cooking(self, line_id):
        line = self.env["pos.kitchen.ticket.line"].browse(line_id)
        if line.state not in LINE_TRANSITIONS:
            return
        if "cooking" not in LINE_TRANSITIONS.get(line.state, set()):
            return
        line.state = "cooking"
        self._sync_state_from_lines()
        self.env["bus.bus"]._sendone(
            f"pos_kitchen.{self.pos_config_id.id}", "notification", {
                "res_model": "pos.kitchen.ticket.line",
                "message": "pos_order_line_cooking",
                "line_id": line.id,
                "ticket_id": self.id,
                "config_id": self.pos_config_id.id,
            })

    def action_line_ready(self, line_id):
        line = self.env["pos.kitchen.ticket.line"].browse(line_id)
        if line.state not in LINE_TRANSITIONS:
            return
        if "ready" not in LINE_TRANSITIONS.get(line.state, set()):
            return
        line.state = "ready"
        self._sync_state_from_lines()
        self.env["bus.bus"]._sendone(
            f"pos_kitchen.{self.pos_config_id.id}", "notification", {
                "res_model": "pos.kitchen.ticket.line",
                "message": "pos_order_line_ready",
                "line_id": line.id,
                "ticket_id": self.id,
                "config_id": self.pos_config_id.id,
            })

    def action_line_cancel(self, line_id):
        line = self.env["pos.kitchen.ticket.line"].browse(line_id)
        if line.state not in LINE_TRANSITIONS:
            return
        if "cancelled" not in LINE_TRANSITIONS.get(line.state, set()):
            return
        line.state = "cancelled"
        self._sync_state_from_lines()
        self.env["bus.bus"]._sendone(
            f"pos_kitchen.{self.pos_config_id.id}", "notification", {
                "res_model": "pos.kitchen.ticket.line",
                "message": "pos_order_line_cancelled",
                "line_id": line.id,
                "ticket_id": self.id,
                "config_id": self.pos_config_id.id,
            })

    @api.model
    def get_details(self, shop_id):
        tickets = self.search([
            ("pos_config_id", "=", shop_id),
            ("state", "not in", ["delivered", "cancelled"]),
        ], order="create_date desc")

        result = []
        all_categories = set()
        for ticket in tickets:
            lines = []
            for l in ticket.line_ids:
                lines.append({
                    "id": l.id,
                    "product_id": l.product_id.id,
                    "pos_order_line_id": l.pos_order_line_id.id,
                    "full_product_name": l.full_product_name,
                    "qty_total": l.qty_total,
                    "qty_sent": l.qty_sent,
                    "qty_ready": l.qty_ready,
                    "qty_cancelled": l.qty_cancelled,
                    "note": _extract_note_text(l.note),
                    "state": l.state,
                    "product_category": l.product_category or "",
                })
                cat = l.product_category or ""
                if cat:
                    all_categories.add(cat)
            result.append({
                "id": ticket.id,
                "origin_pos_order_id": ticket.origin_pos_order_id.id,
                "pos_reference": ticket.pos_reference,
                "order_name": ticket.order_name,
                "ticket_type": ticket.ticket_type,
                "batch_letter": ticket.batch_letter,
                "sequence": ticket.sequence,
                "state": ticket.state,
                "payment_status": ticket.payment_status,
                "table_id": ticket.table_id.id if ticket.table_id else False,
                "table_name": ticket.table_id.display_name if ticket.table_id else "",
                "partner_name": ticket.partner_id.display_name if ticket.partner_id else "",
                "date_order": ticket.create_date,
                "requested_time": ticket.requested_time or False,
                "lines": lines,
                "config_id": ticket.pos_config_id.id,
                "session_id": ticket.session_id.id if ticket.session_id else False,
            })

        stations = [{"id": cat, "name": cat} for cat in sorted(all_categories)]
        return {"tickets": result, "stations": stations}

    @api.model
    def get_or_create_ticket(self, pos_order):
        ticket = self.search([
            ("origin_pos_order_id", "=", pos_order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if ticket:
            return ticket

        kitchen_screen = self.env["kitchen.screen"].search([
            ("pos_config_id", "=", pos_order.config_id.id)
        ], limit=1)
        if not kitchen_screen:
            return False

        has_kitchen = False
        for order_line in pos_order.lines:
            if order_line.product_id.pos_categ_ids and any(
                    c.id in kitchen_screen.pos_categ_ids.ids
                    for c in order_line.product_id.pos_categ_ids):
                has_kitchen = True
                break

        if not has_kitchen:
            return False

        sequence = self.env["ir.sequence"].next_by_code("kitchen.ticket") or "KITCHEN-0001"
        payment_status = "paid" if pos_order.state == "paid" else "not_paid"

        ticket = self.create({
            "origin_pos_order_id": pos_order.id,
            "sequence": sequence,
            "ticket_type": "new",
            "batch_letter": "A",
            "payment_status": payment_status,
        })
        line_vals = []
        for order_line in pos_order.lines:
            if order_line.product_id.pos_categ_ids and any(
                    c.id in kitchen_screen.pos_categ_ids.ids
                    for c in order_line.product_id.pos_categ_ids):
                qty = order_line.qty
                product_category = self._get_product_category(order_line.product_id)
                line_vals.append((0, 0, {
                    "pos_order_line_id": order_line.id,
                    "qty_total": qty,
                    "qty_sent": qty,
                    "note": _extract_note_text(order_line.note),
                    "state": "pending",
                    "product_category": product_category,
                }))
        if line_vals:
            ticket.write({"line_ids": line_vals})
        ticket._notify_kitchen("pos_order_created")
        return ticket

    def get_full_order_lines(self, pos_order):
        line_vals = []
        for order_line in pos_order.lines:
            product_category = self._get_product_category(order_line.product_id)
            line_vals.append((0, 0, {
                "pos_order_line_id": order_line.id,
                "qty_total": order_line.qty,
                "qty_sent": order_line.qty,
                "note": order_line.note or "",
                "state": "pending",
                "product_category": product_category,
            }))
        return line_vals

    @api.model
    def create_delta_tickets(self, pos_order):
        kitchen_screen = self.env["kitchen.screen"].search([
            ("pos_config_id", "=", pos_order.config_id.id)
        ], limit=1)
        if not kitchen_screen:
            return []

        existing_tickets = self.search([
            ("origin_pos_order_id", "=", pos_order.id),
        ])
        used_letters = set(existing_tickets.mapped("batch_letter"))
        tickets_created = []

        for order_line in pos_order.lines:
            if not (order_line.product_id.pos_categ_ids and any(
                    c.id in kitchen_screen.pos_categ_ids.ids
                    for c in order_line.product_id.pos_categ_ids)):
                continue

            current_qty = order_line.qty
            sent_qty = order_line.qty_sent_to_kitchen
            delta = current_qty - sent_qty

            if delta == 0:
                continue

            if delta > 0:
                next_letter = self._next_batch_letter(used_letters)
                used_letters.add(next_letter)
                sequence = self.env["ir.sequence"].next_by_code("kitchen.ticket") or "KITCHEN-0001"
                payment_status = "paid" if pos_order.state == "paid" else "not_paid"

                ticket = self.create({
                    "origin_pos_order_id": pos_order.id,
                    "sequence": sequence,
                    "ticket_type": "addition",
                    "batch_letter": next_letter,
                    "state": "pending",
                    "payment_status": payment_status,
                })
                self.env["pos.kitchen.ticket.line"].create({
                    "ticket_id": ticket.id,
                    "pos_order_line_id": order_line.id,
                    "qty_total": abs(delta),
                    "qty_sent": abs(delta),
                    "note": _extract_note_text(order_line.note),
                    "state": "pending",
                    "product_category": self._get_product_category(order_line.product_id),
                })
                order_line.qty_sent_to_kitchen = current_qty
                ticket._notify_kitchen("pos_order_created")
                tickets_created.append(ticket)

            elif delta < 0:
                next_letter = self._next_batch_letter(used_letters)
                used_letters.add(next_letter)
                sequence = self.env["ir.sequence"].next_by_code("kitchen.ticket") or "KITCHEN-0001"
                payment_status = "paid" if pos_order.state == "paid" else "not_paid"

                ticket = self.create({
                    "origin_pos_order_id": pos_order.id,
                    "sequence": sequence,
                    "ticket_type": "cancellation",
                    "batch_letter": next_letter,
                    "state": "pending",
                    "payment_status": payment_status,
                })
                self.env["pos.kitchen.ticket.line"].create({
                    "ticket_id": ticket.id,
                    "pos_order_line_id": order_line.id,
                    "qty_total": abs(delta),
                    "qty_sent": abs(delta),
                    "note": _extract_note_text(order_line.note),
                    "state": "cancelled",
                    "product_category": self._get_product_category(order_line.product_id),
                })
                order_line.qty_sent_to_kitchen = current_qty
                ticket._notify_kitchen("pos_order_created")
                tickets_created.append(ticket)

        return tickets_created

    @staticmethod
    def _next_batch_letter(used):
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in used:
                return letter
        return "Z"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("sequence", "Nuevo") == "Nuevo":
                vals["sequence"] = self.env["ir.sequence"].next_by_code(
                    "kitchen.ticket") or "Nuevo"
        return super().create(vals_list)


class PosKitchenTicketLine(models.Model):
    _name = "pos.kitchen.ticket.line"
    _description = "Kitchen Ticket Line"

    ticket_id = fields.Many2one(
        "pos.kitchen.ticket", string="Ticket", required=True, ondelete="cascade")
    pos_order_line_id = fields.Many2one(
        "pos.order.line", string="Linea de orden", required=True, ondelete="cascade")
    product_id = fields.Many2one(
        "product.product", related="pos_order_line_id.product_id", store=True)
    full_product_name = fields.Char(
        related="pos_order_line_id.full_product_name", store=True)
    note = fields.Char(string="Nota")
    product_category = fields.Char(
        string="Categoria de Producto",
        help="Categoria para enrutamiento por estacion")

    qty_total = fields.Float(string="Cantidad total", default=1.0)
    qty_sent = fields.Float(string="Cantidad enviada", default=1.0)
    qty_ready = fields.Float(string="Cantidad lista", default=0.0)
    qty_cancelled = fields.Float(string="Cantidad cancelada", default=0.0)

    state = fields.Selection([
        ("pending", "Pendiente"),
        ("cooking", "En Horno"),
        ("waiting", "Esperando Espacio"),
        ("ready", "Listo"),
        ("cancelled", "Cancelado"),
    ], default="pending", string="Estado")

    def action_cooking(self):
        self.ensure_one()
        if "cooking" not in LINE_TRANSITIONS.get(self.state, set()):
            return
        self.state = "cooking"
        self.ticket_id._sync_state_from_lines()
        self.env["bus.bus"]._sendone(
            f"pos_kitchen.{self.ticket_id.pos_config_id.id}", "notification", {
                "res_model": self._name,
                "message": "pos_order_line_cooking",
                "line_id": self.id,
                "ticket_id": self.ticket_id.id,
                "config_id": self.ticket_id.pos_config_id.id,
            })

    def action_ready(self):
        self.ensure_one()
        if "ready" not in LINE_TRANSITIONS.get(self.state, set()):
            return
        self.state = "ready"
        self.ticket_id._sync_state_from_lines()
        self.env["bus.bus"]._sendone(
            f"pos_kitchen.{self.ticket_id.pos_config_id.id}", "notification", {
                "res_model": self._name,
                "message": "pos_order_line_ready",
                "line_id": self.id,
                "ticket_id": self.ticket_id.id,
                "config_id": self.ticket_id.pos_config_id.id,
            })

    def action_cancel(self):
        self.ensure_one()
        if "cancelled" not in LINE_TRANSITIONS.get(self.state, set()):
            return
        self.state = "cancelled"
        self.ticket_id._sync_state_from_lines()
        self.env["bus.bus"]._sendone(
            f"pos_kitchen.{self.ticket_id.pos_config_id.id}", "notification", {
                "res_model": self._name,
                "message": "pos_order_line_cancelled",
                "line_id": self.id,
                "ticket_id": self.ticket_id.id,
                "config_id": self.ticket_id.pos_config_id.id,
            })

    def action_toggle(self):
        self.ensure_one()
        cycle = {
            "pending": "cooking",
            "cooking": "ready",
            "ready": "cancelled",
            "cancelled": "pending",
        }
        new_state = cycle.get(self.state, "pending")
        self.state = new_state
        self.ticket_id._sync_state_from_lines()
        self.env["bus.bus"]._sendone(
            f"pos_kitchen.{self.ticket_id.pos_config_id.id}", "notification", {
                "res_model": self._name,
                "message": "pos_order_line_updated",
                "line_id": self.id,
                "ticket_id": self.ticket_id.id,
                "config_id": self.ticket_id.pos_config_id.id,
                "new_status": new_state,
            })