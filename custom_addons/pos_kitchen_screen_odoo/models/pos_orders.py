# -*- coding: utf-8 -*-
from odoo import api, fields, models


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
                KitchenTicket.get_or_create_ticket(order)
        return res

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        for order in self:
            tickets = self.env["pos.kitchen.ticket"].search([
                ("origin_pos_order_id", "=", order.id),
                ("state", "not in", ["cancelled"]),
            ])
            if tickets:
                tickets.write({"payment_status": "paid"})
                for ticket in tickets:
                    ticket._notify_kitchen("pos_order_paid")
            else:
                self.env["pos.kitchen.ticket"].get_or_create_ticket(order)
        return res

    @api.model
    def process_order_for_kitchen(self, order_data):
        pos_order = self.search([
            ("pos_reference", "=", str(order_data.get("pos_reference", ""))),
            ("config_id", "=", order_data.get("config_id", 0)),
        ], limit=1)
        if not pos_order:
            return False
        tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(pos_order)
        return [t.id for t in tickets] if tickets else False

    def print_customer_receipt(self):
        self.ensure_one()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", self.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(self)
        if ticket:
            return ticket.print_ticket()
        return False
