from odoo import fields, models


class PlanningBatchShortage(models.Model):
    _name = 'planning.batch.shortage'
    _description = 'Planning Batch Shortage'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='batch_id.company_id',
        store=True,
        string='Company',
        readonly=True,
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
    level = fields.Integer(string='Level', default=0, index=True)
    demand_qty = fields.Float(string='Demand Qty')
    available_qty = fields.Float(string='Available Qty')
    shortage_qty = fields.Float(string='Shortage Qty')
    source_type = fields.Selection(
        [
            ('so', 'SO'),
            ('mo', 'MO'),
            ('po', 'PO'),
        ],
        string='Source Type',
        required=True,
        default='so',
    )
    related_line_ids = fields.Many2many(
        comodel_name='sale.order.line',
        relation='planning_batch_shortage_sale_line_rel',
        column1='shortage_id',
        column2='sale_line_id',
        string='Related Sales Order Lines',
        readonly=True,
    )
