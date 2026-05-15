# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

# Kitchen tickets extend pos.order with qty_sent_to_kitchen tracking.
# pos.order.line._load_pos_data_fields includes qty_sent_to_kitchen.
# No session-level overrides needed for Odoo 19's pos.load.mixin.
