# -*- coding: utf-8 -*-
"""Single synchronization boundary between POS orders and the kitchen projection.

This service owns:
- The bus channel name (so backend and frontend never drift apart)
- The sync_order() entry point (so delta creation has one caller)
- The notify() method (so all bus payloads carry order_id + ticket_id)
- The _affects_kitchen() guard (so we skip sync for non-kitchen writes)
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# ── Channel constant (single source of truth) ──────────────────────────
# KDS frontend subscribes to:  pos_kitchen.{config_id}
# Backend publishes to:        pos_kitchen.{config_id}
# If these ever differ, real-time push silently breaks.
KITCHEN_BUS_CHANNEL = "pos_kitchen.{}"


class PosKitchenSync(models.AbstractModel):
    _name = "pos.kitchen.sync"
    _description = "Kitchen Projection Synchronization"

    # ── Public API ─────────────────────────────────────────────────────

    @api.model
    def sync_order(self, order):
        """Reconcile kitchen projection with current POS order state.

        Called after any write to pos.order that may affect the kitchen
        projection.  Idempotent — safe to call multiple times.
        """
        kitchen_screen = self.env["kitchen.screen"].search([
            ("pos_config_id", "=", order.config_id.id),
        ], limit=1)
        if not kitchen_screen:
            _logger.info("[SYNC] sync_order: no kitchen screen for config %s", order.config_id.id)
            return

        existing = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        if not existing:
            _logger.info("[SYNC] sync_order: no base ticket for order %s, skipping", order.pos_reference)
            return

        _logger.info("[SYNC] sync_order: running delta check for order %s", order.pos_reference)
        self.env["pos.kitchen.ticket"].create_delta_tickets(order)

    @api.model
    def notify(self, message_type, order_id, config_id, ticket_id=None, line_id=None, **kwargs):
        """Send a standardized bus notification to all KDS clients.

        Every notification MUST carry order_id so the KDS can do
        per-order reloads instead of fetching all tickets.
        """
        channel = KITCHEN_BUS_CHANNEL.format(config_id)
        payload = {
            "message": message_type,
            "order_id": order_id,
            "config_id": config_id,
            "ticket_id": ticket_id,
        }
        if line_id:
            payload["line_id"] = line_id
        payload.update(kwargs)

        _logger.info("[SYNC] notify channel=%s message=%s order=%s ticket=%s",
                     channel, message_type, order_id, ticket_id)
        self.env["bus.bus"]._sendone(channel, "notification", payload)

    @api.model
    def sync_and_notify(self, order, message_type="pos_order_updated"):
        """Sync the projection, then notify KDS clients.

        Convenience that combines the two most common operations.
        """
        self.sync_order(order)
        base_ticket = self.env["pos.kitchen.ticket"].search([
            ("origin_pos_order_id", "=", order.id),
            ("ticket_type", "=", "new"),
        ], limit=1)
        self.notify(
            message_type,
            order_id=order.id,
            config_id=order.config_id.id,
            ticket_id=base_ticket.id if base_ticket else None,
        )

    # ── Affects-guard ──────────────────────────────────────────────────

    @api.model
    def _affects_kitchen(self, vals):
        """Return True if the written vals may affect the kitchen projection.

        Avoids calling create_delta_tickets() on every state change, payment
        update, or other non-kitchen write to pos.order.
        """
        kitchen_fields = {
            "lines",
            "order_type",
            "requested_time",
            "table_id",
            "partner_id",
        }
        return bool(kitchen_fields & set(vals.keys()))
