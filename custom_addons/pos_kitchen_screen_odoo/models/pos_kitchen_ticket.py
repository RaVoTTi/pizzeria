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
        ("waiting", "Esperando Espacio"),
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
    requested_time = fields.Datetime(string="Hora solicitada", help="Hora en que el cliente quiere el pedido")

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
        oven_capacity = self._get_oven_capacity()
        cooking_tickets = self.search([
            ("pos_config_id", "=", self.pos_config_id.id),
            ("state", "=", "cooking"),
        ])
        total_pizzas = 0
        for ticket in cooking_tickets:
            for line in ticket.line_ids:
                cat = (line.product_category or "").lower()
                if "pizza" in cat or "empanada" in cat or "mitad" in cat:
                    total_pizzas += line.qty_total
        if total_pizzas >= oven_capacity:
            self.state = "waiting"
            self._notify_kitchen("pos_order_waiting")
            return False
        self.state = "cooking"
        self.started_at = fields.Datetime.now()
        self._notify_kitchen("pos_order_accepted")
        return True

    def progress_to_waiting(self):
        self.ensure_one()
        self.state = "waiting"
        self._notify_kitchen("pos_order_waiting")

    def progress_from_waiting(self):
        self.ensure_one()
        oven_capacity = self._get_oven_capacity()
        cooking_tickets = self.search([
            ("pos_config_id", "=", self.pos_config_id.id),
            ("state", "=", "cooking"),
        ])
        total_pizzas = 0
        for ticket in cooking_tickets:
            for line in ticket.line_ids:
                cat = (line.product_category or "").lower()
                if "pizza" in cat or "empanada" in cat or "mitad" in cat:
                    total_pizzas += line.qty_total
        if total_pizzas < oven_capacity:
            self.state = "cooking"
            self.started_at = fields.Datetime.now()
            self._notify_kitchen("pos_order_accepted")
            return True
        return False

    def _get_oven_capacity(self):
        ks = self.env["kitchen.screen"].search([
            ("pos_config_id", "=", self.pos_config_id.id),
        ], limit=1)
        return ks.oven_capacity if ks and ks.oven_capacity else 6

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

    def print_ticket(self, with_logo=True):
        self.ensure_one()
        printer = self._get_printer_name()
        if not printer:
            _logger.warning("No printer configured for kitchen screen")
            return False
        ticket_str = self._format_ticket_escpos()
        data = ticket_str.encode("latin-1")
        if with_logo:
            try:
                from odoo.addons.pos_receipt_logo.models.receipt_logo import ReceiptLogo
                logo_bytes = ReceiptLogo.get_logo_escpos_bytes()
                data = data + b"\x1b@" + logo_bytes
            except Exception:
                pass
        try:
            result = subprocess.run(
                ["lp", "-d", printer, "-o", "raw"],
                input=data,
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

    def _get_all_order_lines(self):
        """Get all lines from the POS order, including drinks and other items."""
        pos_order = self.origin_pos_order_id
        if not pos_order:
            return self.line_ids
        
        all_lines = []
        for order_line in pos_order.lines:
            all_lines.append({
                "qty_total": order_line.qty,
                "full_product_name": order_line.full_product_name or order_line.product_id.name,
                "note": order_line.note or "",
                "state": "pending",
                "product_category": self._get_product_category(order_line.product_id),
                "product_id": order_line.product_id,
            })
        return all_lines

    def _get_printer_name(self):
        ks = self.env["kitchen.screen"].search([
            ("pos_config_id", "=", self.pos_config_id.id),
        ], limit=1)
        return ks.printer_name if ks else None

    def _format_ticket_escpos(self):
        ESC = "\x1b"
        REV_ON = ESC + "\x1dB\x01"
        REV_OFF = ESC + "\x1dB\x00"
        BOLD = ESC + "!\x08"
        DBLH = ESC + "!\x10"
        DBLW = ESC + "!\x20"
        DBLHW = ESC + "!\x30"
        NORM = ESC + "!\x00"
        UNDER = ESC + "\x2d\x01"
        NOUNDR = ESC + "\x2d\x00"
        DIVIDER = "-" * 42

        lines = []
        lines.append(ESC + "@")

        seq_num = (self.sequence or "0001").replace("KT-", "") if self.sequence and self.sequence != "Nuevo" else "0001"
        batch = self.batch_letter or "A"

        header_parts = f"#{seq_num} {batch}"
        if self.partner_id:
            name = self.partner_id.name.upper()
            remaining = 42 - len(header_parts) - 1
            if remaining > 3 and len(name) > remaining:
                name = name[:remaining - 1] + "."
            header_parts = f"{header_parts} {name}"

        lines.append(f"{BOLD}{header_parts}{NORM}")

        type_parts = []
        if self.table_id:
            type_parts.append(f"MESA {self.table_id.table_number}")
        elif self.partner_id and self.partner_id.street:
            type_parts.append("DELIVERY")

        payment_label = "PAGADO" if self.payment_status == "paid" else ""
        if self.payment_status != "paid" and self.ticket_type != "cancellation":
            payment_label = "NO PAGADO"

        if payment_label:
            type_parts.append(payment_label)

        if self.ticket_type != "new":
            type_labels = {
                "addition": "ADICION",
                "cancellation": "CANCELACION",
                "modification": "MODIF",
            }
            tl = type_labels.get(self.ticket_type, "")
            if tl:
                type_parts.append(tl)

        if self.requested_time:
            type_parts.append(self.requested_time.strftime("%H:%M"))
        elif self.create_date:
            type_parts.append(self.create_date.strftime("%H:%M"))

        if type_parts:
            lines.append(f"{BOLD}{' | '.join(type_parts)}{NORM}")

        lines.append(DIVIDER)

        all_lines = self._get_all_order_lines()

        categories = {"Pizza": [], "Empanada": [], "Bebida": [], "Otro": []}
        for line in all_lines:
            if hasattr(line, 'product_category'):
                cat = line.product_category or ""
                qty = line.qty_total
                name = line.full_product_name or ""
                note = line.note or ""
                state = line.state
            else:
                cat = line.get("product_category", "")
                qty = line.get("qty_total", 1)
                name = line.get("full_product_name", "")
                note = line.get("note", "")
                state = line.get("state", "pending")

            entry = {"qty": qty, "name": name, "note": note, "state": state}
            if cat in categories:
                categories[cat].append(entry)
            else:
                categories["Otro"].append(entry)

        cat_order = [
            ("Pizza", "PIZZAS"),
            ("Empanada", "EMPANADAS"),
            ("Bebida", "BEBIDAS"),
            ("Otro", "OTROS"),
        ]

        for cat_key, cat_label in cat_order:
            items = categories.get(cat_key, [])
            if not items:
                continue
            lines.append(f"{BOLD}{cat_label}{NORM}")
            for item in items:
                qty = int(item["qty"]) if item["qty"] == int(item["qty"]) else item["qty"]
                name = item["name"][:30].upper()
                qty_str = f"{qty}x"
                lines.append(f" {qty_str:>3} {name}")
                if item["note"]:
                    lines.append(f"     {REV_ON} {item['note'][:28].upper()} {REV_OFF}")
            lines.append("")

        order_notes = []
        order = self.origin_pos_order_id
        if order and order.general_customer_note:
            order_notes.append(order.general_customer_note)
        if order_notes:
            lines.append(DIVIDER)
            lines.append(f"{BOLD}OBSERVACIONES{NORM}")
            for n in order_notes:
                for part in n.split('\n')[:3]:
                    lines.append(f"  {part[:38].upper()}")

        if self.partner_id and self.partner_id.street:
            lines.append(DIVIDER)
            lines.append(f"{BOLD}DIRECCION:{NORM} {self.partner_id.street}")
            if self.partner_id.street2:
                lines.append(f"  {self.partner_id.street2}")

        lines.append(DIVIDER)
        created_time = self.create_date.strftime("%H:%M") if self.create_date else ""
        if created_time:
            lines.append(f"CREADO {created_time}")

        lines.append(ESC + "d" + "\x03")

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
                    "note": l.note or "",
                    "state": l.state,
                    "product_category": l.product_category or "",
                })
                cat = l.product_category or ""
                if cat and 'mitad' not in cat.lower():
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
                    "note": order_line.note or "",
                    "state": "pending",
                    "product_category": product_category,
                }))
                order_line.qty_sent_to_kitchen = qty
        if line_vals:
            ticket.write({"line_ids": line_vals})
        ticket._notify_kitchen("pos_order_created")
        return ticket

    def get_full_order_lines(self, pos_order):
        """Get all order lines including drinks, not just kitchen items."""
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
                    "note": order_line.note or "",
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

    def _get_product_category(self, product):
        name = (product.name or "").lower()
        if "pizza" in name or "mitad" in name or "panini" in name:
            return "Pizza"
        if "empanada" in name:
            return "Empanada"
        if "cerveza" in name or "bebida" in name:
            return "Bebida"
        return "Otro"

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
    product_category = fields.Char(
        string="Categoria de Producto",
        help="Categoria para enrutamiento por estacion (Pizza, Empanada, etc.)")

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
