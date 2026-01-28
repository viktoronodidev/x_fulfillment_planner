from odoo import fields, models


class PlanningBatchBomIssue(models.Model):
    _name = 'planning.batch.bom_issue'
    _description = 'Planning Batch BOM Issue'

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
