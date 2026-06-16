# -*- coding: utf-8 -*-
"""
Comprehensive KDS test suite following the testing pyramid:
- 20% Unit tests (state machine, transitions)
- 60% Integration/Scenario tests (projections, deltas, undo, concurrency)
- 20% End-to-end tests (full kitchen workflows)
"""
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestKDSStateMachine(TransactionCase):
    """Unit tests for line state transitions."""

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
        cls.partner = cls.env["res.partner"].create({"name": "Test Client"})
        cls.pos_category = cls.env["pos.category"].create({"name": "Pizzas"})
        cls.product = cls.env["product.product"].create({
            "name": "Test Pizza",
            "type": "consu",
            "list_price": 10.0,
            "available_in_pos": True,
            "pos_categ_ids": [(6, 0, [cls.pos_category.id])],
        })
        cls.kitchen_screen = cls.env["kitchen.screen"].create({
            "pos_config_id": cls.pos_config.id,
            "pos_categ_ids": [(6, 0, [cls.pos_category.id])],
        })

    def _close_all_sessions(self):
        self.env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE state != 'closed'")

    def _cleanup_kitchen_screens(self):
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket_line")
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket")
        self.env["kitchen.screen"].search([]).unlink()

    def _create_pos_order(self, qty=1.0, note=""):
        self._close_all_sessions()
        session = self.env["pos.session"].with_context(onboarding_creation=True).create({
            "config_id": self.pos_config.id,
        })
        total = qty * 10.0
        line_vals = {
            "product_id": self.product.id,
            "qty": qty,
            "price_unit": 10.0,
            "price_subtotal": total,
            "price_subtotal_incl": total,
        }
        if note:
            line_vals["note"] = note
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
            "lines": [(0, 0, line_vals)],
        })
        return order

    def test_pending_goes_to_cooking(self):
        """Test basic forward transition: pending → cooking."""
        self._cleanup_kitchen_screens()
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        line = ticket.line_ids[0]
        self.assertEqual(line.state, "pending")
        line.action_cooking()
        self.assertEqual(line.state, "cooking")

    def test_cooking_goes_to_ready(self):
        """Test forward transition: cooking → ready."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        line = ticket.line_ids[0]
        line.action_cooking()
        line.action_ready()
        self.assertEqual(line.state, "ready")

    def test_ready_goes_to_cancelled(self):
        """Test forward transition: ready → cancelled."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        line = ticket.line_ids[0]
        line.action_cooking()
        line.action_ready()
        line.action_cancel()
        self.assertEqual(line.state, "cancelled")

    def test_cancelled_goes_to_pending(self):
        """Test cycle: cancelled → pending."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        line = ticket.line_ids[0]
        line.action_cancel()
        line.action_toggle()
        self.assertEqual(line.state, "pending")

    def test_previous_from_cooking_goes_to_pending(self):
        """Test backward transition: cooking → pending."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        line = ticket.line_ids[0]
        line.action_cooking()
        self.assertEqual(line.state, "cooking")
        line.action_previous()
        self.assertEqual(line.state, "pending")

    def test_previous_from_ready_goes_to_cooking(self):
        """Test backward transition: ready → cooking."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        line = ticket.line_ids[0]
        line.action_cooking()
        line.action_ready()
        self.assertEqual(line.state, "ready")
        line.action_previous()
        self.assertEqual(line.state, "cooking")

    def test_previous_from_cancelled_goes_to_ready(self):
        """Test backward transition: cancelled → ready."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        line = ticket.line_ids[0]
        line.action_cooking()
        line.action_ready()
        line.action_cancel()
        self.assertEqual(line.state, "cancelled")
        line.action_previous()
        self.assertEqual(line.state, "ready")


@tagged('post_install', '-at_install')
class TestKDSProjections(TransactionCase):
    """Integration tests for stage projections."""

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
        cls.partner = cls.env["res.partner"].create({"name": "Test Client"})
        cls.pizza_category = cls.env["pos.category"].create({"name": "Pizzas"})
        cls.empanada_category = cls.env["pos.category"].create({"name": "Empanadas"})
        cls.pizza_product = cls.env["product.product"].create({
            "name": "Margarita",
            "type": "consu",
            "list_price": 10.0,
            "available_in_pos": True,
            "pos_categ_ids": [(6, 0, [cls.pizza_category.id])],
        })
        cls.empanada_product = cls.env["product.product"].create({
            "name": "Empanada Carne",
            "type": "consu",
            "list_price": 5.0,
            "available_in_pos": True,
            "pos_categ_ids": [(6, 0, [cls.empanada_category.id])],
        })
        cls.kitchen_screen = cls.env["kitchen.screen"].create({
            "pos_config_id": cls.pos_config.id,
            "pos_categ_ids": [(6, 0, [cls.pizza_category.id, cls.empanada_category.id])],
        })

    def _close_all_sessions(self):
        self.env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE state != 'closed'")

    def _cleanup_kitchen_screens(self):
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket_line")
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket")
        self.env["kitchen.screen"].search([]).unlink()

    def _create_multi_line_order(self):
        """Create an order with pizza + empanada."""
        self._close_all_sessions()
        session = self.env["pos.session"].with_context(onboarding_creation=True).create({
            "config_id": self.pos_config.id,
        })
        order = self.env["pos.order"].create({
            "company_id": self.company.id,
            "session_id": session.id,
            "partner_id": self.partner.id,
            "pricelist_id": self.pos_config.pricelist_id.id,
            "config_id": self.pos_config.id,
            "amount_tax": 0.0,
            "amount_total": 15.0,
            "amount_paid": 15.0,
            "amount_return": 0.0,
            "lines": [
                (0, 0, {
                    "product_id": self.pizza_product.id,
                    "qty": 2,
                    "price_unit": 10.0,
                    "price_subtotal": 20.0,
                    "price_subtotal_incl": 20.0,
                }),
                (0, 0, {
                    "product_id": self.empanada_product.id,
                    "qty": 1,
                    "price_unit": 5.0,
                    "price_subtotal": 5.0,
                    "price_subtotal_incl": 5.0,
                }),
            ],
        })
        return order

    def test_projection_groups_lines_by_stage(self):
        """Test that get_details returns lines grouped correctly for projections."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pizza_category.id, self.empanada_category.id])],
        })
        order = self._create_multi_line_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        pizza_line = ticket.line_ids.filtered(lambda l: l.product_id == self.pizza_product)
        empanada_line = ticket.line_ids.filtered(lambda l: l.product_id == self.empanada_product)
        pizza_line.action_cooking()
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        self.assertIsNotNone(ticket_data)
        pizza_lines = [l for l in ticket_data["lines"] if l["product_id"] == self.pizza_product.id]
        empanada_lines = [l for l in ticket_data["lines"] if l["product_id"] == self.empanada_product.id]
        self.assertEqual(pizza_lines[0]["state"], "cooking")
        self.assertEqual(empanada_lines[0]["state"], "pending")

    def test_multi_stage_projection_pending_tab(self):
        """Test pending projection shows pending lines as active, others as context."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pizza_category.id, self.empanada_category.id])],
        })
        order = self._create_multi_line_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        pizza_line = ticket.line_ids.filtered(lambda l: l.product_id == self.pizza_product)
        pizza_line.action_cooking()
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        empanada_lines = [l for l in ticket_data["lines"] if l["product_id"] == self.empanada_product.id]
        self.assertEqual(empanada_lines[0]["state"], "pending")

    def test_multi_stage_projection_cooking_tab(self):
        """Test cooking projection shows cooking lines as active."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pizza_category.id, self.empanada_category.id])],
        })
        order = self._create_multi_line_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        pizza_line = ticket.line_ids.filtered(lambda l: l.product_id == self.pizza_product)
        pizza_line.action_cooking()
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        pizza_lines = [l for l in ticket_data["lines"] if l["product_id"] == self.pizza_product.id]
        self.assertEqual(pizza_lines[0]["state"], "cooking")


@tagged('post_install', '-at_install')
class TestKDSDeltaTickets(TransactionCase):
    """Integration tests for delta ticket creation (additions/cancellations)."""

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
        cls.partner = cls.env["res.partner"].create({"name": "Test Client"})
        cls.pos_category = cls.env["pos.category"].create({"name": "Pizzas"})
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

    def _close_all_sessions(self):
        self.env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE state != 'closed'")

    def _cleanup_kitchen_screens(self):
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket_line")
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket")
        self.env["kitchen.screen"].search([]).unlink()

    def _create_pos_order(self, qty=2.0, note=""):
        self._close_all_sessions()
        session = self.env["pos.session"].with_context(onboarding_creation=True).create({
            "config_id": self.pos_config.id,
        })
        total = qty * 10.0
        line_vals = {
            "product_id": self.product.id,
            "qty": qty,
            "price_unit": 10.0,
            "price_subtotal": total,
            "price_subtotal_incl": total,
        }
        if note:
            line_vals["note"] = note
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
            "lines": [(0, 0, line_vals)],
        })
        return order

    def test_quantity_increase_creates_addition_ticket(self):
        """Test that increasing qty creates an addition delta ticket."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(qty=2.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        self.assertEqual(order.lines.qty_sent_to_kitchen, 2.0)
        order.lines.qty = 3.0
        tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(order)
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].ticket_type, "addition")
        self.assertEqual(tickets[0].batch_letter, "B")
        self.assertEqual(tickets[0].line_ids.qty_total, 1.0)
        self.assertEqual(order.lines.qty_sent_to_kitchen, 3.0)

    def test_quantity_decrease_creates_cancellation_ticket(self):
        """Test that decreasing qty creates a cancellation delta ticket."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(qty=3.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        self.assertEqual(order.lines.qty_sent_to_kitchen, 3.0)
        order.lines.qty = 1.0
        tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(order)
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].ticket_type, "cancellation")
        self.assertEqual(tickets[0].batch_letter, "B")
        self.assertEqual(tickets[0].line_ids.qty_total, 2.0)
        self.assertEqual(tickets[0].line_ids.state, "cancelled")
        self.assertEqual(order.lines.qty_sent_to_kitchen, 1.0)

    def test_note_change_updates_in_place_without_delta(self):
        """Test that note-only changes update the existing line in-place."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(qty=2.0, note="Sin cebolla")
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        line = ticket.line_ids[0]
        self.assertEqual(line.note, "Sin cebolla")
        self.assertEqual(line.note_snapshot, "Sin cebolla")
        self.assertFalse(line.note_modified)
        order.lines.note = "Sin cebolla, sin ajo"
        delta_tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(order)
        self.assertEqual(len(delta_tickets), 0)
        line.invalidate_recordset()
        line = self.env["pos.kitchen.ticket.line"].browse(line.id)
        self.assertEqual(line.note, "Sin cebolla, sin ajo")
        self.assertEqual(line.note_snapshot, "Sin cebolla, sin ajo")
        self.assertTrue(line.note_modified)

    def test_note_and_qty_change_regression(self):
        """
        REGRESSION TEST: Note + qty change simultaneously.
        This was a critical bug where the delta ticket line was dropped
        due to deduplication by pos_order_line_id.
        """
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(qty=2.0, note="Sin cebolla")
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        base_line = ticket.line_ids[0]
        self.assertEqual(base_line.qty_total, 2.0)
        self.assertEqual(base_line.note, "Sin cebolla")
        order.lines.qty = 3.0
        order.lines.note = "Sin cebolla, sin ajo"
        delta_tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(order)
        self.assertEqual(len(delta_tickets), 1, "Should create addition ticket for qty increase")
        self.assertEqual(delta_tickets[0].ticket_type, "addition")
        self.assertEqual(delta_tickets[0].line_ids.qty_total, 1.0, "Delta should be qty 1")
        base_line.invalidate_recordset()
        base_line = self.env["pos.kitchen.ticket.line"].browse(base_line.id)
        self.assertEqual(base_line.note, "Sin cebolla, sin ajo", "Base line note should be updated")
        self.assertTrue(base_line.note_modified, "Base line should be marked as modified")
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        self.assertIsNotNone(ticket_data)
        total_qty = sum(l["qty_total"] for l in ticket_data["lines"])
        self.assertEqual(total_qty, 3.0, "Merged card should show total qty 3")


@tagged('post_install', '-at_install')
class TestKDSUndo(TransactionCase):
    """Integration tests for undo functionality."""

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
        cls.partner = cls.env["res.partner"].create({"name": "Test Client"})
        cls.pos_category = cls.env["pos.category"].create({"name": "Pizzas"})
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

    def _close_all_sessions(self):
        self.env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE state != 'closed'")

    def _cleanup_kitchen_screens(self):
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket_line")
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket")
        self.env["kitchen.screen"].search([]).unlink()

    def _create_pos_order(self, qty=1.0):
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

    def test_card_advancement_undo(self):
        """Test that reverting a card returns it to previous state."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        self.assertEqual(ticket.state, "pending")
        ticket.progress_to_cooking()
        self.assertEqual(ticket.state, "cooking")
        ticket.revert_to_previous()
        self.assertEqual(ticket.state, "pending")
        self.assertEqual(ticket.line_ids[0].state, "pending")

    def test_multiple_advancement_undo(self):
        """Test undo after multiple advancements."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        ticket.progress_to_cooking()
        ticket.progress_to_ready()
        self.assertEqual(ticket.state, "ready")
        ticket.revert_to_previous()
        self.assertEqual(ticket.state, "cooking")
        self.assertEqual(ticket.line_ids[0].state, "cooking")


@tagged('post_install', '-at_install')
class TestKDSConcurrency(TransactionCase):
    """Integration tests for multi-screen concurrency scenarios."""

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
        cls.partner = cls.env["res.partner"].create({"name": "Test Client"})
        cls.pos_category = cls.env["pos.category"].create({"name": "Pizzas"})
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

    def _close_all_sessions(self):
        self.env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE state != 'closed'")

    def _cleanup_kitchen_screens(self):
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket_line")
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket")
        self.env["kitchen.screen"].search([]).unlink()

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

    def test_two_cooks_advance_same_ticket(self):
        """Test that two cooks advancing the same ticket doesn't cause issues."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order(qty=2.0)
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        line = ticket.line_ids[0]
        line.action_cooking()
        self.assertEqual(line.state, "cooking")
        line.action_cooking()
        self.assertEqual(line.state, "cooking", "Second advance should be no-op")

    def test_cancel_while_progressing(self):
        """Test cancel and progress happening in sequence."""
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pos_category.id])],
        })
        order = self._create_pos_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        ticket.progress_to_cooking()
        self.assertEqual(ticket.state, "cooking")
        ticket.cancel_ticket()
        self.assertEqual(ticket.state, "cancelled")
        self.assertEqual(ticket.line_ids[0].state, "cancelled")


@tagged('post_install', '-at_install')
class TestKDSEndToEnd(TransactionCase):
    """End-to-end scenario tests simulating real kitchen workflows."""

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
        cls.partner = cls.env["res.partner"].create({"name": "Test Client"})
        cls.pizza_category = cls.env["pos.category"].create({"name": "Pizzas"})
        cls.empanada_category = cls.env["pos.category"].create({"name": "Empanadas"})
        cls.pizza_product = cls.env["product.product"].create({
            "name": "Margarita",
            "type": "consu",
            "list_price": 10.0,
            "available_in_pos": True,
            "pos_categ_ids": [(6, 0, [cls.pizza_category.id])],
        })
        cls.empanada_product = cls.env["product.product"].create({
            "name": "Empanada Carne",
            "type": "consu",
            "list_price": 5.0,
            "available_in_pos": True,
            "pos_categ_ids": [(6, 0, [cls.empanada_category.id])],
        })
        cls.kitchen_screen = cls.env["kitchen.screen"].create({
            "pos_config_id": cls.pos_config.id,
            "pos_categ_ids": [(6, 0, [cls.pizza_category.id, cls.empanada_category.id])],
        })

    def _close_all_sessions(self):
        self.env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE state != 'closed'")

    def _cleanup_kitchen_screens(self):
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket_line")
        self.env.cr.execute("DELETE FROM pos_kitchen_ticket")
        self.env["kitchen.screen"].search([]).unlink()

    def _create_multi_line_order(self):
        self._close_all_sessions()
        session = self.env["pos.session"].with_context(onboarding_creation=True).create({
            "config_id": self.pos_config.id,
        })
        order = self.env["pos.order"].create({
            "company_id": self.company.id,
            "session_id": session.id,
            "partner_id": self.partner.id,
            "pricelist_id": self.pos_config.pricelist_id.id,
            "config_id": self.pos_config.id,
            "amount_tax": 0.0,
            "amount_total": 15.0,
            "amount_paid": 15.0,
            "amount_return": 0.0,
            "lines": [
                (0, 0, {
                    "product_id": self.pizza_product.id,
                    "qty": 2,
                    "price_unit": 10.0,
                    "price_subtotal": 20.0,
                    "price_subtotal_incl": 20.0,
                }),
                (0, 0, {
                    "product_id": self.empanada_product.id,
                    "qty": 1,
                    "price_unit": 5.0,
                    "price_subtotal": 5.0,
                    "price_subtotal_incl": 5.0,
                }),
            ],
        })
        return order

    def test_scenario_dinner_service_basic(self):
        """
        Scenario 1: Basic dinner service workflow.
        Order arrives → Cook starts pizzas → Waiter changes note →
        Cook acknowledges → Order delivered
        """
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pizza_category.id, self.empanada_category.id])],
        })
        order = self._create_multi_line_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        self.assertEqual(ticket.state, "pending")
        self.assertEqual(len(ticket.line_ids), 2)
        pizza_line = ticket.line_ids.filtered(lambda l: l.product_id == self.pizza_product)
        empanada_line = ticket.line_ids.filtered(lambda l: l.product_id == self.empanada_product)
        pizza_line.action_cooking()
        self.assertEqual(pizza_line.state, "cooking")
        self.assertEqual(empanada_line.state, "pending")
        order.lines.filtered(lambda l: l.product_id == self.pizza_product).note = "Sin ajo"
        self.env["pos.kitchen.ticket"].create_delta_tickets(order)
        pizza_line.invalidate_recordset()
        self.assertTrue(pizza_line.note_modified)
        pizza_line.acknowledge_modification()
        self.assertFalse(pizza_line.note_modified)
        pizza_line.action_ready()
        empanada_line.action_cooking()
        empanada_line.action_ready()
        ticket.progress_to_delivered()
        self.assertEqual(ticket.state, "delivered")
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        self.assertIsNone(ticket_data, "Delivered ticket should not appear in active details")

    def test_scenario_partial_cooking_cancel_undo_continue(self):
        """
        Scenario 2: Partial cooking → Cancel → Undo → Continue → Deliver.
        Tests that cancel + undo preserves line states correctly.
        """
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pizza_category.id, self.empanada_category.id])],
        })
        order = self._create_multi_line_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        pizza_line = ticket.line_ids.filtered(lambda l: l.product_id == self.pizza_product)
        empanada_line = ticket.line_ids.filtered(lambda l: l.product_id == self.empanada_product)
        pizza_line.action_cooking()
        self.assertEqual(pizza_line.state, "cooking")
        self.assertEqual(empanada_line.state, "pending")
        ticket.cancel_ticket()
        self.assertEqual(ticket.state, "cancelled")
        self.assertEqual(pizza_line.state, "cancelled")
        self.assertEqual(empanada_line.state, "cancelled")
        pizza_line.action_toggle()
        empanada_line.action_toggle()
        self.assertEqual(pizza_line.state, "pending")
        self.assertEqual(empanada_line.state, "pending")
        pizza_line.action_cooking()
        pizza_line.action_ready()
        empanada_line.action_cooking()
        empanada_line.action_ready()
        ticket.progress_to_delivered()
        self.assertEqual(ticket.state, "delivered")
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        self.assertFalse(any(t["id"] == ticket.id for t in details["tickets"]))

    def test_monster_scenario_full_workflow(self):
        """
        Monster scenario: Full workflow with all operations.
        Create order → Move lines → Modify note → Increase qty → Cancel → Undo → Deliver.
        Validates state machine, projections, deltas, modifications, undo at every step.
        """
        self._cleanup_kitchen_screens()
        self.kitchen_screen = self.env["kitchen.screen"].create({
            "pos_config_id": self.pos_config.id,
            "pos_categ_ids": [(6, 0, [self.pizza_category.id, self.empanada_category.id])],
        })
        order = self._create_multi_line_order()
        ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        self.assertEqual(ticket.state, "pending")
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        self.assertIsNotNone(ticket_data)
        pizza_line = ticket.line_ids.filtered(lambda l: l.product_id == self.pizza_product)
        empanada_line = ticket.line_ids.filtered(lambda l: l.product_id == self.empanada_product)
        pizza_line.action_cooking()
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        pizza_data = next((l for l in ticket_data["lines"] if l["product_id"] == self.pizza_product.id), None)
        self.assertEqual(pizza_data["state"], "cooking")
        pizza_line.action_ready()
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        pizza_data = next((l for l in ticket_data["lines"] if l["product_id"] == self.pizza_product.id), None)
        self.assertEqual(pizza_data["state"], "ready")
        order.lines.filtered(lambda l: l.product_id == self.empanada_product).note = "Sin cebolla"
        self.env["pos.kitchen.ticket"].create_delta_tickets(order)
        empanada_line.invalidate_recordset()
        self.assertTrue(empanada_line.note_modified)
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        empanada_data = next((l for l in ticket_data["lines"] if l["product_id"] == self.empanada_product.id), None)
        self.assertEqual(empanada_data["qty_total"], 1.0)
        order.lines.filtered(lambda l: l.product_id == self.empanada_product).qty = 2.0
        delta_tickets = self.env["pos.kitchen.ticket"].create_delta_tickets(order)
        self.assertEqual(len(delta_tickets), 1)
        self.assertEqual(delta_tickets[0].ticket_type, "addition")
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        ticket_data = next((t for t in details["tickets"] if t["id"] == ticket.id), None)
        total_qty = sum(l["qty_total"] for l in ticket_data["lines"])
        self.assertEqual(total_qty, 4.0, "Total should be 2 pizzas + 2 empanadas")
        ticket.cancel_ticket()
        self.assertEqual(ticket.state, "cancelled")
        for line in ticket.line_ids:
            line.action_toggle()
        self.assertEqual(pizza_line.state, "pending")
        self.assertEqual(empanada_line.state, "pending")
        pizza_line.action_cooking()
        pizza_line.action_ready()
        empanada_line.action_cooking()
        empanada_line.action_ready()
        ticket.progress_to_delivered()
        self.assertEqual(ticket.state, "delivered")
        details = self.env["pos.kitchen.ticket"].get_details(self.pos_config.id)
        self.assertFalse(any(t["id"] == ticket.id for t in details["tickets"]))
