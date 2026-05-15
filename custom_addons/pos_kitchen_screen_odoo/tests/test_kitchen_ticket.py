# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestKitchenTicketWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(user=cls.env.ref("base.user_admin"))

        cls.pos_config = cls.env["pos.config"].search([], limit=1)
        if not cls.pos_config:
            cls.pos_config = cls.env["pos.config"].create({
                "name": "POS Test",
                "module_pos_restaurant": True,
            })
        cls.company = cls.pos_config.company_id
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Prueba"})

        cls._close_all_sessions()
        cls._cleanup_kitchen_screens()

        cls.pos_category = cls.env["pos.category"].create({
            "name": "Pizzas",
        })

        cls.product = cls.env["product.product"].create({
            "name": "Margarita",
            "type": "consu",
            "list_price": 10.0,
            "available_in_pos": True,
            "pos_categ_ids": [(6, 0, [cls.pos_category.id])],
        })

        cls.kitchen_screen = cls.env["kitchen.screen"].create({
            "pos_config_id": cls.pos_config.id,
            "pos_categ_ids": [(6, 0, [cls.pos_category.id])],
        })

    @classmethod
    def _close_all_sessions(cls):
        cls.env.cr.execute(
            "UPDATE pos_session SET state = 'closed' WHERE state != 'closed'"
        )

    @classmethod
    def _cleanup_kitchen_screens(cls):
        cls.env.cr.execute("DELETE FROM pos_kitchen_ticket_line")
        cls.env.cr.execute("DELETE FROM pos_kitchen_ticket")
        cls.env["kitchen.screen"].search([]).unlink()

    def _create_pos_order(self, qty=2.0):
        self._close_all_sessions()
        session = self.env["pos.session"].with_context(onboarding_creation=True).create({
            "config_id": self.pos_config.id,
        })
        total = qty * 10.0
        order = self.env["pos.order"].create({
            "company_id": self.company.id,
            "session_id": session.id,
            "partner_id": self.partner.id,
            "pricelist_id": self.pos_config.pricelist_id.id,
            "config_id": self.pos_config.id,
            "amount_tax": 0.0,
            "amount_total": total,
            "amount_paid": total,
            "amount_return": 0.0,
            "lines": [(0, 0, {
                "product_id": self.product.id,
                "qty": qty,
                "price_unit": 10.0,
                "price_subtotal": total,
                "price_subtotal_incl": total,
            })],
        })
        return order

    def test_ticket_auto_created_on_order(self):
        order = self._create_pos_order(2.0)
        tickets = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ])
        self.assertEqual(len(tickets), 1, "Ticket auto-created on pos.order.create")
        self.assertEqual(tickets.state, "pending")
        self.assertEqual(tickets.batch_letter, "A")
        self.assertEqual(len(tickets.line_ids), 1)
        self.assertEqual(tickets.line_ids.qty_total, 2.0)
        self.assertEqual(tickets.line_ids.qty_sent, 2.0)
        self.assertEqual(tickets.line_ids.state, "pending")

    def test_ticket_created_via_get_or_create(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(2.0)
        ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(order)

        self.assertTrue(ticket, "Debe existir un ticket tipo 'new'")
        self.assertEqual(ticket.state, "pending")
        self.assertEqual(ticket.batch_letter, "A")
        self.assertEqual(len(ticket.line_ids), 1)
        self.assertEqual(ticket.line_ids.qty_total, 2.0)
        self.assertEqual(ticket.line_ids.qty_sent, 2.0)
        self.assertEqual(ticket.line_ids.state, "pending")

    def test_ticket_is_immutable_no_duplicate(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(2.0)
        self.env["pos.kitchen.ticket"].get_or_create_ticket(order)
        self.env["pos.kitchen.ticket"].get_or_create_ticket(order)

        tickets = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ])
        self.assertEqual(len(tickets), 1, "No deben crearse duplicados del ticket nuevo")

    def test_line_state_cycle(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(1.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(order)

        line = ticket.line_ids[0]
        self.assertEqual(line.state, "pending")

        line.action_cooking()
        self.assertEqual(line.state, "cooking")

        line.action_ready()
        self.assertEqual(line.state, "ready")

        line.action_cancel()
        self.assertEqual(line.state, "cancelled")

        line.action_toggle()
        self.assertEqual(line.state, "pending")

    def test_ticket_state_advance(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(1.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(order)

        self.assertEqual(ticket.state, "pending")

        ticket.progress_to_cooking()
        self.assertEqual(ticket.state, "cooking")
        self.assertTrue(ticket.started_at)

        ticket.progress_to_ready()
        self.assertEqual(ticket.state, "ready")
        self.assertTrue(ticket.ready_at)
        self.assertEqual(ticket.line_ids.state, "ready")

        ticket.progress_to_delivered()
        self.assertEqual(ticket.state, "delivered")
        self.assertTrue(ticket.delivered_at)

    def test_cancel_ticket(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(1.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(order)

        ticket.cancel_ticket()
        self.assertEqual(ticket.state, "cancelled")

    def test_delta_addition_ticket(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(2.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(order)

        self.assertEqual(order.lines.qty_sent_to_kitchen, 2.0)

        order.lines.qty = 3.0
        tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(order)

        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].ticket_type, "addition")
        self.assertEqual(tickets[0].batch_letter, "B")
        self.assertEqual(tickets[0].line_ids.qty_total, 1.0)
        self.assertEqual(order.lines.qty_sent_to_kitchen, 3.0)

    def test_delta_cancellation_ticket(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(3.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(order)

        self.assertEqual(order.lines.qty_sent_to_kitchen, 3.0)

        order.lines.qty = 1.0
        tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(order)

        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].ticket_type, "cancellation")
        self.assertEqual(tickets[0].batch_letter, "B")
        self.assertEqual(tickets[0].line_ids.qty_total, 2.0)
        self.assertEqual(tickets[0].line_ids.state, "cancelled")
        self.assertEqual(order.lines.qty_sent_to_kitchen, 1.0)

    def test_no_delta_when_unchanged(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(2.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(order)

        tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(order)
        self.assertEqual(len(tickets), 0)

    def test_get_details_returns_active_tickets(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(1.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not ticket:
            ticket = self.env["pos.kitchen.ticket"].get_or_create_ticket(order)

        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        self.assertTrue(any(d["id"] == ticket.id for d in details))

        ticket.cancel_ticket()
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        self.assertFalse(any(d["id"] == ticket.id for d in details))

    def test_payment_status_updates_on_paid(self):
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(2.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
        ], limit=1)
        self.assertTrue(ticket, "Ticket should exist after order creation")
        self.assertEqual(ticket.payment_status, "not_paid",
                         "Ticket starts as not_paid when order is unpaid")

        order.action_pos_order_paid()

        ticket.invalidate_recordset()
        ticket = self.env["pos.kitchen.ticket"].browse(ticket.id)
        self.assertEqual(ticket.payment_status, "paid",
                         "Ticket payment_status should be paid after order is paid")

    def test_no_kitchen_ticket_without_screen(self):
        self._cleanup_kitchen_screens()
        order = self._create_pos_order(2.0)
        tickets = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
        ])
        self.assertEqual(len(tickets), 0,
                         "No ticket should be created when no kitchen screen exists")

    def test_no_kitchen_ticket_without_category_match(self):
        self._cleanup_kitchen_screens()
        other_category = self.env["pos.category"].create({"name": "Other"})
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [other_category.id])],
        })
        order = self._create_pos_order(2.0)
        tickets = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
        ])
        self.assertEqual(len(tickets), 0,
                         "No ticket for order with non-matching category")