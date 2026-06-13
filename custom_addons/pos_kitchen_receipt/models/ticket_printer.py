# -*- coding: utf-8 -*-
import json
import logging
import subprocess

from odoo import models

_logger = logging.getLogger(__name__)


class TicketPrinter(models.AbstractModel):
    _name = "kitchen.ticket.printer"
    _description = "Kitchen ticket ESC/POS formatting and printing"

    def format_ticket_escpos(self, ticket, with_cut=True):
        ESC = "\x1b"
        REV_ON = ESC + "\x1dB\x01"
        REV_OFF = ESC + "\x1dB\x00"
        BOLD = ESC + "!\x08"
        NORM = ESC + "!\x00"
        DBLH = ESC + "!\x10"
        DBLHW = ESC + "!\x30"
        DIVIDER = "-" * 42
        CUT = ESC + "i"

        order_type = ticket.order_type
        if not order_type:
            if ticket.table_id:
                order_type = 'mesa'
            elif ticket.partner_id and ticket.partner_id.street:
                order_type = 'delivery'
            else:
                order_type = 'retira'

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
        if order_type == 'mesa':
            table_num = ticket.table_id.table_number if ticket.table_id else "?"
            lines.append(f"{DBLHW}MESA {table_num}{NORM}")
        elif order_type == 'delivery':
            type_parts.append("DELIVERY")
        else:
            type_parts.append("RETIRA")

        if ticket.payment_status != "paid" and ticket.ticket_type != "cancellation":
            type_parts.append("FALTA PAGAR")

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
            type_parts.append(f"Entrega: {ticket.requested_time.strftime('%H:%M')}")

        if ticket.create_date:
            type_parts.append(f"Creado: {ticket.create_date.strftime('%H:%M')}")

        if type_parts:
            lines.append(f"{DBLH}{' | '.join(type_parts)}{NORM}")

        lines.append(DIVIDER)

        all_lines = self._get_all_order_lines(ticket)
        categories = {"Pizza": [], "Empanada": [], "Bebida": [], "Envio": [], "Otro": []}

        for line in all_lines:
            qty = line.get("qty_total", 1)
            if qty == 0:
                continue
            cat = line.get("product_category", "")
            entry = {
                "qty": qty,
                "name": line.get("full_product_name", ""),
                "note": line.get("note", ""),
                "state": line.get("state", "pending"),
            }
            if cat in categories:
                categories[cat].append(entry)
            else:
                categories["Otro"].append(entry)

        cat_order = [
            ("Empanada", "EMPANADAS"),
            ("Bebida", "BEBIDAS"),
            ("Envio", "ENVIO"),
            ("Otro", "OTROS"),
        ]

        pizza_items = categories.get("Pizza", [])
        if pizza_items:
            pizza_labels = {
                'mesa': "PIZZAS SALON",
                'delivery': "PIZZAS DELIVERY",
                'retira': "PIZZAS RETIRA",
            }
            pizza_label = pizza_labels.get(order_type, "PIZZAS SALON")
            lines.append(f"{BOLD}{pizza_label}{NORM}")
            for item in pizza_items:
                qty = int(item["qty"]) if item["qty"] == int(item["qty"]) else item["qty"]
                name = self._truncate_name(item["name"].upper(), 21)
                qty_str = f"{qty}x"
                lines.append(f"{DBLH} {qty_str:>3} {name}{NORM}")
                note_texts = self._extract_note_text(item["note"])
                for nt in note_texts:
                    lines.append(f"     > {nt[:28].upper()}")
            lines.append("")

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
                note_texts = self._extract_note_text(item["note"])
                for nt in note_texts:
                    lines.append(f"     > {nt[:28].upper()}")
            lines.append("")

        order = ticket.origin_pos_order_id
        if order and order.general_customer_note:
            lines.append(DIVIDER)
            lines.append(f"{BOLD}OBSERVACIONES{NORM}")
            for part in order.general_customer_note.split('\n')[:3]:
                lines.append(f"  {part[:38].upper()}")

        lines.append(DIVIDER)
        order = ticket.origin_pos_order_id
        if order and hasattr(order, 'amount_total') and order.amount_total:
            total_str = f"${order.amount_total:,.0f}" if order.amount_total == int(order.amount_total) else f"${order.amount_total:,.2f}"
            lines.append(f"{DBLHW}TOTAL: {total_str}{NORM}")

        if order_type == 'delivery' and ticket.partner_id:
            street = (ticket.partner_id.street or "").strip()
            street2 = (ticket.partner_id.street2 or "").strip()
            if street:
                lines.append(DIVIDER)
                lines.append(f"{DBLH}  {street[:38]}{NORM}")
                if street2:
                    lines.append(f"{DBLH}  {street2[:38]}{NORM}")
            else:
                lines.append(DIVIDER)
                lines.append(f"{BOLD}  VER DIRECCION EN SISTEMA{NORM}")

        lines.append(ESC + "d" + "\x03")
        if with_cut:
            lines.append(CUT)

        return "\n".join(lines) + "\n"

    def print_ticket(self, ticket, with_logo=True):
        printer = self._get_printer_name(ticket)
        if not printer:
            _logger.warning("No printer configured for kitchen screen")
            return False
        ticket_str = self.format_ticket_escpos(ticket, with_cut=False)
        data = ticket_str.encode("utf-8", errors="replace")
        if with_logo:
            try:
                from odoo.addons.pos_kitchen_receipt.models._logo import get_logo_escpos_bytes
                logo_bytes = get_logo_escpos_bytes()
                if logo_bytes:
                    data = data + logo_bytes + b"\x1bd\x08"
            except Exception:
                pass
        data = data + b"\x1bi"
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
    def _extract_note_text(note_value):
        if not note_value:
            return []
        if isinstance(note_value, str):
            try:
                parsed = json.loads(note_value)
            except (json.JSONDecodeError, TypeError):
                stripped = note_value.strip()
                return [stripped] if stripped else []
        else:
            parsed = note_value
        if isinstance(parsed, list):
            parts = [item.get("text", "") for item in parsed if isinstance(item, dict) and item.get("text")]
            return parts
        if isinstance(parsed, dict):
            text = parsed.get("text", "")
            return [text] if text else []
        stripped = str(parsed).strip()
        return [stripped] if stripped else []

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
            if "pizza" in cat_name:
                return "Pizza"
            if "empanada" in cat_name:
                return "Empanada"
            if "delivery" in cat_name or "envio" in cat_name:
                return "Envio"
            if "cerveza" in cat_name or "bebida" in cat_name:
                return "Bebida"
        name = (product.name or "").lower()
        if "pizza" in name or "panini" in name:
            return "Pizza"
        if "empanada" in name:
            return "Empanada"
        if "envio" in name or "delivery" in name:
            return "Envio"
        if "cerveza" in name or "bebida" in name:
            return "Bebida"
        return "Otro"