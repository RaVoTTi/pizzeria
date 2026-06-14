# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    def print_thermal_receipt(self):
        self.ensure_one()
        _logger.info("[Thermal Print] print_thermal_receipt called for order %s (id=%s)", self.name, self.id)
        
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", self.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        _logger.info("[Thermal Print] Found ticket: %s", ticket)
        
        if not ticket:
            _logger.info("[Thermal Print] No ticket found, creating one...")
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(self)
            _logger.info("[Thermal Print] Created ticket: %s", ticket)
        
        if ticket:
            _logger.info("[Thermal Print] Printing ticket %s...", ticket.sequence)
            result = self.env["kitchen.ticket.printer"].print_ticket(ticket)
            _logger.info("[Thermal Print] Print result: %s", result)
            return result
        
        _logger.warning("[Thermal Print] No ticket available to print")
        return False
