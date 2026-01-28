from odoo import fields, models


class PlanningBatchProductSummary(models.Model):
    _name = 'planning.batch.product_summary'
    _description = 'Planning Batch Product Summary'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UoM',
        required=True,
    )
    qty = fields.Float(string='Quantity')
