from odoo import fields, models


class PlanningBatchSelectSOProduct(models.TransientModel):
    _name = 'planning.batch.select.so.product'
    _description = 'Select Sales Orders Product Summary'

    wizard_id = fields.Many2one(
        comodel_name='planning.batch.select.so',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UoM',
        required=True,
    )
    qty = fields.Float(string='Quantity')
