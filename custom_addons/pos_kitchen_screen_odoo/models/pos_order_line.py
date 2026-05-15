from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    qty_sent_to_kitchen = fields.Float(
        default=0.0,
        help="Cantidad ya enviada a cocina. Se usa para detectar adiciones o cancelaciones."
    )

    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list.append("qty_sent_to_kitchen")
        return fields_list
