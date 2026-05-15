# -*- coding: utf-8 -*-
import logging
import subprocess

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosKitchenTicket(models.Model):
    _name = "pos.kitchen.ticket"
    _description = "Kitchen Ticket — append-only operational event"
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
        help="Letra de lote: A para el original, B/C/D para adiciones o cancelaciones posteriores")

    ticket_type = fields.Selection([
        ("new", "Nuevo"),
        ("addition", "Adicion"),
        ("cancellation", "Cancelacion"),
        ("modification", "Modificacion"),
    ], default="new", required=True, string="Tipo")

    state = fields.Selection([
        ("pending", "Pendiente"),
        ("cooking", "En Horno"),
        ("ready", "Listo"),
        ("delivered", "Entregado"),
        ("cancelled", "Cancelado"),
    ], default="pending", string="Estado")

    payment_status = fields.Selection([
        ("paid", "Pagado"),
        ("not_paid", "No Pagado"),
    ], default="not_paid", string="Estado de Pago",
    help="Estado de pago al momento de crear el ticket (snapshot)")

    line_ids = fields.One2many(
        "pos.kitchen.ticket.line", "ticket_id", string="Lineas")

    created_at = fields.Datetime(string="Creado", default=lambda self: fields.Datetime.now())
    started_at = fields.Datetime(string="Iniciado")
    ready_at = fields.Datetime(string="Listo a las")
    delivered_at = fields.Datetime(string="Entregado a las")

    def _notify_kitchen(self, message_type):
        self.ensure_one()
        msg = {
            "res_model": self._name,
            "message": message_type,
            "ticket_id": self.id,
            "config_id": self.pos_config_id.id,
        }
        channel = f"pos_order_created_{self.pos_config_id.id}"
        self.env["bus.bus"]._sendone(channel, "notification", msg)

    def progress_to_cooking(self):
        self.ensure_one()
        self.state = "cooking"
        self.started_at = fields.Datetime.now()
        self._notify_kitchen("pos_order_accepted")

    def progress_to_ready(self):
        self.ensure_one()
        self.state = "ready"
        self.ready_at = fields.Datetime.now()
        self.line_ids.write({"state": "ready"})
        self._notify_kitchen("pos_order_completed")

    def progress_to_delivered(self):
        self.ensure_one()
        self.state = "delivered"
        self.delivered_at = fields.Datetime.now()
        self._notify_kitchen("pos_order_delivered")

    def cancel_ticket(self):
        self.ensure_one()
        self.state = "cancelled"
        self._notify_kitchen("pos_order_cancelled")

    def print_ticket(self):
        self.ensure_one()
        printer = self._get_printer_name()
        if not printer:
            _logger.warning("No printer configured for kitchen screen")
            return False
        data = self._format_ticket_escpos()
        try:
            result = subprocess.run(
                ["lp", "-d", printer, "-o", "raw"],
                input=data.encode("latin-1"),
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                _logger.error(
                    "Kitchen print failed for ticket %s: %s",
                    self.sequence, result.stderr.decode()
                )
                return False
            _logger.info("Kitchen ticket %s printed to %s", self.sequence, printer)
            return True
        except FileNotFoundError:
            _logger.error("CUPS lp command not found on this server")
            return False
        except Exception as e:
            _logger.error("Kitchen print error for ticket %s: %s", self.sequence, str(e))
            return False

    def _get_printer_name(self):
        ks = self.env["kitchen.screen"].search([
            ("pos_config_id", "=", self.pos_config_id.id),
        ], limit=1)
        return ks.printer_name if ks else None

    def _format_ticket_escpos(self):
        ESC = "\x1b"
        lines = []

        lines.append(ESC + "@")

        lines.append(ESC + "a" + "\x01")
        lines.append(ESC + "!" + "\x30")
        lines.append("PIZZERIA EL GORDO")
        lines.append("")

        lines.append(ESC + "!" + "\x00")
        ticket_type_names = {
            "new": "NUEVO PEDIDO",
            "addition": "ADICION",
            "cancellation": "CANCELACION",
            "modification": "MODIFICACION",
        }
        type_label = ticket_type_names.get(self.ticket_type, self.ticket_type)
        lines.append(f"Ticket: {self.sequence}-{self.batch_letter}")
        lines.append(f"Tipo: {type_label}")
        lines.append(f"Orden: {self.pos_reference or self.order_name}")
        
        payment_label = "PAGADO" if self.payment_status == "paid" else "NO PAGADO"
        lines.append(f"Pago: {payment_label}")

        if self.table_id:
            lines.append(f"Mesa: {self.table_id.name}")
        if self.partner_id:
            lines.append(f"Cliente: {self.partner_id.name}")

        lines.append("")
        lines.append("-" * 40)
        lines.append("CANT  PRODUCTO")
        lines.append("-" * 40)

        for line in self.line_ids:
            state_label = {
                "pending": "",
                "cooking": "[HORNO]",
                "ready": "[LISTO]",
                "cancelled": "[CANC]",
            }.get(line.state, "")
            name = getattr(line, "full_product_name", "") or line.product_id.name
            name = name[:30]
            lines.append(f"{line.qty_total:>4.0f}x {name} {state_label}")
            if line.note:
                lines.append(f"      ! {line.note[:28]}")

        lines.append("-" * 40)

        now = fields.Datetime.now()
        lines.append(f"Impreso: {now}")
        lines.append("")

        lines.append(ESC + "d" + "\x04")
        lines.append(ESC + "i")

        return "\n".join(lines) + "\n"

    def action_line_cooking(self, line_id):
        line = self.env["pos.kitchen.ticket.line"].browse(line_id)
        line.state = "cooking"
        msg = {
            "res_model": "pos.kitchen.ticket.line",
            "message": "pos_order_line_cooking",
            "line_id": line.id,
            "ticket_id": self.id,
            "config_id": self.pos_config_id.id,
        }
        channel = f"pos_order_created_{self.pos_config_id.id}"
        self.env["bus.bus"]._sendone(channel, "notification", msg)

    def action_line_ready(self, line_id):
        line = self.env["pos.kitchen.ticket.line"].browse(line_id)
        line.state = "ready"
        msg = {
            "res_model": "pos.kitchen.ticket.line",
            "message": "pos_order_line_ready",
            "line_id": line.id,
            "ticket_id": self.id,
            "config_id": self.pos_config_id.id,
        }
        channel = f"pos_order_created_{self.pos_config_id.id}"
        self.env["bus.bus"]._sendone(channel, "notification", msg)

    def action_line_cancel(self, line_id):
        line = self.env["pos.kitchen.ticket.line"].browse(line_id)
        line.state = "cancelled"
        msg = {
            "res_model": "pos.kitchen.ticket.line",
            "message": "pos_order_line_cancelled",
            "line_id": line.id,
            "ticket_id": self.id,
            "config_id": self.pos_config_id.id,
        }
        channel = f"pos_order_created_{self.pos_config_id.id}"
        self.env["bus.bus"]._sendone(channel, "notification", msg)

    @api.model
    def get_details(self, shop_id):
        tickets = self.search([
            ("pos_config_id", "=", shop_id),
            ("state", "not in", ["delivered", "cancelled"]),
        ], order="create_date desc")

        result = []
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
                    "note": l.note or "",
                    "state": l.state,
                })
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
                "lines": lines,
                "config_id": ticket.pos_config_id.id,
                "session_id": ticket.session_id.id if ticket.session_id else False,
            })
        return result

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
                line_vals.append((0, 0, {
                    "pos_order_line_id": order_line.id,
                    "qty_total": qty,
                    "qty_sent": qty,
                    "note": order_line.note or "",
                    "state": "pending",
                }))
                order_line.qty_sent_to_kitchen = qty
        if line_vals:
            ticket.write({"line_ids": line_vals})
        ticket._notify_kitchen("pos_order_created")
        return ticket

    @api.model
    def create_delta_tickets(self, pos_order):
        """Detect additions and cancellations, create delta tickets."""
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
                    "note": order_line.note or "",
                    "state": "pending",
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
                    "note": order_line.note or "",
                    "state": "cancelled",
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
    _description = "Kitchen Ticket Line — operational unit"

    ticket_id = fields.Many2one(
        "pos.kitchen.ticket", string="Ticket", required=True, ondelete="cascade")
    pos_order_line_id = fields.Many2one(
        "pos.order.line", string="Linea de orden", required=True, ondelete="cascade")
    product_id = fields.Many2one(
        "product.product", related="pos_order_line_id.product_id", store=True)
    full_product_name = fields.Char(
        related="pos_order_line_id.full_product_name", store=True)
    note = fields.Char(string="Nota")

    qty_total = fields.Float(string="Cantidad total", default=1.0)
    qty_sent = fields.Float(string="Cantidad enviada", default=1.0)
    qty_ready = fields.Float(string="Cantidad lista", default=0.0)
    qty_cancelled = fields.Float(string="Cantidad cancelada", default=0.0)

    state = fields.Selection([
        ("pending", "Pendiente"),
        ("cooking", "En Horno"),
        ("ready", "Listo"),
        ("cancelled", "Cancelado"),
    ], default="pending", string="Estado")

    def action_cooking(self):
        self.ensure_one()
        self.state = "cooking"
        msg = {
            "res_model": self._name,
            "message": "pos_order_line_cooking",
            "line_id": self.id,
            "ticket_id": self.ticket_id.id,
            "config_id": self.ticket_id.pos_config_id.id,
        }
        channel = f"pos_order_created_{self.ticket_id.pos_config_id.id}"
        self.env["bus.bus"]._sendone(channel, "notification", msg)

    def action_ready(self):
        self.ensure_one()
        self.state = "ready"
        msg = {
            "res_model": self._name,
            "message": "pos_order_line_ready",
            "line_id": self.id,
            "ticket_id": self.ticket_id.id,
            "config_id": self.ticket_id.pos_config_id.id,
        }
        channel = f"pos_order_created_{self.ticket_id.pos_config_id.id}"
        self.env["bus.bus"]._sendone(channel, "notification", msg)

    def action_cancel(self):
        self.ensure_one()
        self.state = "cancelled"
        msg = {
            "res_model": self._name,
            "message": "pos_order_line_cancelled",
            "line_id": self.id,
            "ticket_id": self.ticket_id.id,
            "config_id": self.ticket_id.pos_config_id.id,
        }
        channel = f"pos_order_created_{self.ticket_id.pos_config_id.id}"
        self.env["bus.bus"]._sendone(channel, "notification", msg)

    def action_toggle(self):
        self.ensure_one()
        cycle = {
            "pending": "cooking",
            "cooking": "ready",
            "ready": "cancelled",
            "cancelled": "pending",
        }
        self.state = cycle.get(self.state, "pending")
        msg = {
            "res_model": self._name,
            "message": "pos_order_line_updated",
            "line_id": self.id,
            "ticket_id": self.ticket_id.id,
            "config_id": self.ticket_id.pos_config_id.id,
            "new_status": self.state,
        }
        channel = f"pos_order_created_{self.ticket_id.pos_config_id.id}"
        self.env["bus.bus"]._sendone(channel, "notification", msg)
