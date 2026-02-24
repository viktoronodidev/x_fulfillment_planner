from odoo import fields, models


class PlanningBatchChainLine(models.Model):
    _name = 'planning.batch.chain.line'
    _description = 'Planning Batch Manufacturing Chain Line'
    _order = 'root_product_id, level, product_id'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
        index=True,
    )
    root_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Root Product',
        required=True,
        index=True,
    )
    level = fields.Integer(
        string='Level',
        required=True,
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        index=True,
    )
    demand_qty = fields.Float(string='Demand Qty')
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UoM',
        required=True,
    )
    item_type = fields.Selection(
        [
            ('finished', 'Finished'),
            ('semi', 'Semi'),
            ('raw', 'Raw'),
        ],
        string='Item Type',
        required=True,
        default='raw',
    )
    supply_type = fields.Selection(
        [
            ('manufacture', 'Manufacture'),
            ('procure', 'Procure'),
        ],
        string='Supply Type',
        required=True,
        default='procure',
    )
    state = fields.Selection(
        [
            ('ok', 'OK'),
            ('missing_bom', 'Missing BOM'),
            ('cycle', 'Cycle'),
            ('excluded', 'Excluded'),
        ],
        string='State',
        required=True,
        default='ok',
        index=True,
    )
    message = fields.Char(string='Message')
