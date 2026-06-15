# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    order_type = fields.Selection([
        ('mesa', 'Mesa'),
        ('delivery', 'Delivery'),
        ('retira', 'Retira'),
    ], string="Tipo de Orden", default='mesa')

    requested_time = fields.Datetime(string="Hora Solicitada")

    @api.onchange('table_id', 'partner_id')
    def _onchange_order_type(self):
        for order in self:
            if order.table_id:
                order.order_type = 'mesa'
            elif order.partner_id and order.partner_id.street:
                order.order_type = 'delivery'
            else:
                order.order_type = 'retira'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        KitchenTicket = self.env["pos.kitchen.ticket"]
        for order in res:
            kitchen_screen = self.env["kitchen.screen"].search([
                ("pos_config_id", "=", order.config_id.id)
            ], limit=1)
            if kitchen_screen:
                _logger.info("[KITCHEN] Order %s created, creating ticket...", order.pos_reference)
                KitchenTicket.get_or_create_ticket(order)
        return res

    def write(self, vals):
        _logger.info("[KITCHEN] Order write triggered: ids=%s, vals keys=%s", self.ids, list(vals.keys()))
        res = super().write(vals)
        KitchenTicket = self.env["pos.kitchen.ticket"]
        for order in self:
            kitchen_screen = self.env["kitchen.screen"].search([
                ("pos_config_id", "=", order.config_id.id)
            ], limit=1)
            if not kitchen_screen:
                continue
            existing = KitchenTicket.search([
                ("origin_pos_order_id", "=", order.id),
                ("ticket_type", "=", "new"),
            ], limit=1)
            if existing:
                _logger.info("[KITCHEN] Order %s modified, running delta check...", order.pos_reference)
                KitchenTicket.create_delta_tickets(order)
        return res

    def action_pos_order_paid(self):
        _logger.info("[KITCHEN] action_pos_order_paid called for orders: %s", self.ids)
        res = super().action_pos_order_paid()
        for order in self:
            tickets = self.env["pos.kitchen.ticket"].search([
                ("origin_pos_order_id", "=", order.id),
                ("state", "not in", ["cancelled"]),
            ])
            if tickets:
                _logger.info("[KITCHEN] Updating %d tickets to paid for order %s", len(tickets), order.pos_reference)
                tickets.write({"payment_status": "paid"})
                for ticket in tickets:
                    ticket._notify_kitchen("pos_order_paid")
            else:
                _logger.info("[KITCHEN] No active tickets for order %s, creating one", order.pos_reference)
                self.env["pos.kitchen.ticket"].get_or_create_ticket(order)
        return res

    @api.model
    def process_order_for_kitchen(self, order_data):
        _logger.info("[KITCHEN] process_order_for_kitchen called with data: %s", order_data)
        pos_order = self.search([
            ("pos_reference", "=", str(order_data.get("pos_reference", ""))),
            ("config_id", "=", order_data.get("config_id", 0)),
        ], limit=1)
        if not pos_order:
            _logger.info("[KITCHEN] process_order_for_kitchen: order NOT FOUND by pos_reference=%s", order_data.get("pos_reference"))
            return False
        _logger.info("[KITCHEN] process_order_for_kitchen: found order id=%s, running delta check", pos_order.id)
        tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(pos_order)
        _logger.info("[KITCHEN] process_order_for_kitchen: delta tickets created: %s", [t.id for t in tickets] if tickets else [])
        return [t.id for t in tickets] if tickets else False
