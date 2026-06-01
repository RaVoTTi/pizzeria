# -*- coding: utf-8 -*-
import logging
import subprocess

from odoo import models

_logger = logging.getLogger(__name__)


class TicketPrinter(models.AbstractModel):
    _name = "kitchen.ticket.printer"
    _description = "Kitchen ticket ESC/POS formatting and printing"

    def format_ticket_escpos(self, ticket):
        ESC = "\x1b"
        REV_ON = ESC + "\x1dB\x01"
        REV_OFF = ESC + "\x1dB\x00"
        BOLD = ESC + "!\x08"
        NORM = ESC + "!\x00"
        DBLH = ESC + "!\x10"
        DBLHW = ESC + "!\x30"
        DIVIDER = "-" * 42

        lines = []
        lines.append(ESC + "@")

        seq_num = (ticket.sequence or "0001").replace("KT-", "") if ticket.sequence and ticket.sequence != "Nuevo" else "0001"
        batch = ticket.batch_letter or "A"

        header_parts = f"#{seq_num} {batch}"
        if ticket.partner_id:
            name = ticket.partner_id.name.upper()
            remaining = 42 - len(header_parts) - 1
            if remaining > 3 and len(name) > remaining:
                name = name[:remaining - 1] + "."
            if remaining > 3:
                header_parts = f"{header_parts} {name}"

        lines.append(f"{DBLHW}{header_parts}{NORM}")

        type_parts = []
        if ticket.table_id:
            lines.append(f"{DBLHW}MESA {ticket.table_id.table_number}{NORM}")
        elif ticket.partner_id and ticket.partner_id.street:
            type_parts.append("DELIVERY")
        else:
            type_parts.append("RETIRA")

        if ticket.payment_status != "paid" and ticket.ticket_type != "cancellation":
            type_parts.append("NO PAGADO")

        if ticket.ticket_type != "new":
            type_labels = {
                "addition": "ADICION",
                "cancellation": "CANCELACION",
                "modification": "MODIF",
            }
            tl = type_labels.get(ticket.ticket_type, "")
            if tl:
                type_parts.append(tl)

        if ticket.requested_time:
            type_parts.append(ticket.requested_time.strftime("%H:%M"))
        elif ticket.create_date:
            type_parts.append(ticket.create_date.strftime("%H:%M"))

        if type_parts:
            lines.append(f"{DBLH}{' | '.join(type_parts)}{NORM}")

        lines.append(DIVIDER)

        all_lines = self._get_all_order_lines(ticket)
        categories = {"Pizza": [], "Empanada": [], "Bebida": [], "Otro": []}

        for line in all_lines:
            cat = line.get("product_category", "")
            entry = {
                "qty": line.get("qty_total", 1),
                "name": line.get("full_product_name", ""),
                "note": line.get("note", ""),
                "state": line.get("state", "pending"),
            }
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
                name = self._truncate_name(item["name"].upper(), 21)
                qty_str = f"{qty}x"
                lines.append(f"{DBLH} {qty_str:>3} {name}{NORM}")
                if item["note"]:
                    lines.append(f"     {REV_ON} {item['note'][:28].upper()} {REV_OFF}")
            lines.append("")

        order = ticket.origin_pos_order_id
        if order and order.general_customer_note:
            lines.append(DIVIDER)
            lines.append(f"{BOLD}OBSERVACIONES{NORM}")
            for part in order.general_customer_note.split('\n')[:3]:
                lines.append(f"  {part[:38].upper()}")

        if ticket.partner_id and ticket.partner_id.street:
            lines.append(DIVIDER)
            lines.append(f"{BOLD}DIRECCION:{NORM} {ticket.partner_id.street}")
            if ticket.partner_id.street2:
                lines.append(f"  {ticket.partner_id.street2}")

        lines.append(DIVIDER)
        created_time = ticket.create_date.strftime("%H:%M") if ticket.create_date else ""
        if created_time:
            lines.append(f"CREADO {created_time}")

        lines.append(ESC + "d" + "\x03")
        lines.append(ESC + "i")

        return "\n".join(lines) + "\n"

    def print_ticket(self, ticket, with_logo=True):
        printer = self._get_printer_name(ticket)
        if not printer:
            _logger.warning("No printer configured for kitchen screen")
            return False
        ticket_str = self.format_ticket_escpos(ticket)
        data = ticket_str.encode("utf-8", errors="replace")
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
                    ticket.sequence, result.stderr.decode(errors="replace"))
                return False
            _logger.info("Kitchen ticket %s printed to %s", ticket.sequence, printer)
            return True
        except FileNotFoundError:
            _logger.error("CUPS lp command not found on this server")
            return False
        except Exception as e:
            _logger.error("Kitchen print error for ticket %s: %s", ticket.sequence, str(e))
            return False

    def _get_printer_name(self, ticket):
        ks = self.env["kitchen.screen"].search(
            [("pos_config_id", "=", ticket.pos_config_id.id)], limit=1)
        return ks.printer_name if ks else None

    def _get_all_order_lines(self, ticket):
        pos_order = ticket.origin_pos_order_id
        if not pos_order:
            return [{"qty_total": l.qty_total,
                     "full_product_name": l.full_product_name or "",
                     "note": l.note or "",
                     "product_category": l.product_category or "",
                     "state": l.state}
                    for l in ticket.line_ids]
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

    @staticmethod
    def _truncate_name(name, max_len=30):
        if len(name) <= max_len:
            return name
        cut = name[:max_len]
        last_space = cut.rfind(" ")
        if last_space > max_len // 2:
            return cut[:last_space]
        return cut

    def _get_product_category(self, product):
        if product.pos_categ_ids:
            cat_name = product.pos_categ_ids[0].name.lower()
            if "pizza" in cat_name or "mitad" in cat_name:
                return "Pizza"
            if "empanada" in cat_name:
                return "Empanada"
            if "cerveza" in cat_name or "bebida" in cat_name or "delivery" in cat_name:
                return "Bebida"
        name = (product.name or "").lower()
        if "pizza" in name or "mitad" in name or "panini" in name:
            return "Pizza"
        if "empanada" in name:
            return "Empanada"
        if "cerveza" in name or "bebida" in name:
            return "Bebida"
        return "Otro"