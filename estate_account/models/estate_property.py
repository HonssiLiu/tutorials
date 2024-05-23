from odoo import api, fields, models, Command


class EstateProperty(models.Model):
    _inherit = "estate.property"

    def set_state_sold(self):
        moves = self.env['account.move'].create([{
                    'name': self.name,
                    'move_type': 'out_invoice',
                    'partner_id': self.buyer_id.id,
                    'invoice_line_ids': [
                        Command.create({'quantity': self.total_area, 'price_unit': self.selling_price})
                    ]
                }])

        return super().set_state_sold()
