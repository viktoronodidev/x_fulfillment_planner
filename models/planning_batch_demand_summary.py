from odoo import fields, models


class PlanningBatchDemandSummary(models.Model):
    _name = 'planning.batch.demand.summary'
    _description = 'Planning Batch Demand Summary'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        index=True,
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UoM',
        required=True,
    )
    manufacture_demand_qty = fields.Float(string='Manufacture Demand Qty')
    procurement_demand_qty = fields.Float(string='Procurement Demand Qty')
    total_demand_qty = fields.Float(string='Total Demand Qty')
    available_qty = fields.Float(string='Available Qty')
    uncovered_qty = fields.Float(string='Uncovered Qty')
    level_min = fields.Integer(string='Min Level')
    level_max = fields.Integer(string='Max Level')
    has_bom = fields.Boolean(string='Has BOM')
