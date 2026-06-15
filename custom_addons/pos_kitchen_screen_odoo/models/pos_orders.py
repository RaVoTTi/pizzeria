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
    ], string="Tipo de Orden", default='retira')

    requested_time = fields.Datetime(string="Hora Solicitada")

    @api.onchange('table_id', 'partner_id')
    def _onchange_order_type(self):
        for order in self:
            if order.partner_id:
                order.order_type = 'delivery' if order.partner_id.street else 'retira'
            elif order.table_id:
                order.order_type = 'mesa'
            else:
                order.order_type = 'retira'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        Sync = self.env["pos.kitchen.sync"]
        KitchenTicket = self.env["pos.kitchen.ticket"]
        for order in res:
            kitchen_screen = self.env["kitchen.screen"].search([
                ("pos_config_id", "=", order.config_id.id)
            ], limit=1)
            if kitchen_screen:
                _logger.info("[KITCHEN] Order %s created, creating ticket...", order.pos_reference)
                ticket = KitchenTicket.get_or_create_ticket(order)
                if ticket:
                    ticket._notify_kitchen("pos_order_created")
        return res

    def write(self, vals):
        _logger.info("[KITCHEN] Order write: ids=%s vals=%s", self.ids, list(vals.keys()))
        res = super().write(vals)

        if vals.get('state') == 'cancel':
            for order in self:
                tickets = self.env["pos.kitchen.ticket"].search([
                    ("origin_pos_order_id", "=", order.id),
                    ("state", "not in", ["delivered", "cancelled"]),
                ])
                for ticket in tickets:
                    ticket.cancel_ticket()
            return res

        Sync = self.env["pos.kitchen.sync"]
        if Sync._affects_kitchen(vals):
            for order in self:
                Sync.sync_and_notify(order, "pos_order_updated")
        return res

    def action_pos_order_paid(self):
        _logger.info("[KITCHEN] action_pos_order_paid: orders=%s", self.ids)
        res = super().action_pos_order_paid()
        Sync = self.env["pos.kitchen.sync"]
        for order in self:
            tickets = self.env["pos.kitchen.ticket"].search([
                ("origin_pos_order_id", "=", order.id),
                ("state", "not in", ["cancelled"]),
            ])
            if tickets:
                _logger.info("[KITCHEN] Updating %d tickets to paid for order %s", len(tickets), order.pos_reference)
                tickets.write({"payment_status": "paid"})
                for ticket in tickets:
                    Sync.notify("pos_order_paid",
                                order_id=order.id,
                                config_id=order.config_id.id,
                                ticket_id=ticket.id)
            else:
                _logger.info("[KITCHEN] No active tickets for order %s, creating one", order.pos_reference)
                ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(order)
                if ticket:
                    ticket._notify_kitchen("pos_order_paid")
        return res

    @api.model
    def process_order_for_kitchen(self, order_data):
        _logger.info("[KITCHEN] process_order_for_kitchen: data=%s", order_data)
        pos_order = self.search([
            ("pos_reference", "=", str(order_data.get("pos_reference", ""))),
            ("config_id", "=", order_data.get("config_id", 0)),
        ], limit=1)
        if not pos_order:
            _logger.info("[KITCHEN] process_order_for_kitchen: order NOT FOUND by pos_reference=%s", order_data.get("pos_reference"))
            return False
        self.env["pos.kitchen.sync"].sync_and_notify(pos_order, "pos_order_updated")
        return True
