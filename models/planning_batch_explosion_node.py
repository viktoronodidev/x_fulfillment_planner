from odoo import fields, models


class PlanningBatchExplosionNode(models.Model):
    _name = 'planning.batch.explosion.node'
    _description = 'Planning Batch Explosion Node'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'name'

    name = fields.Char(
        string='Node',
        compute='_compute_name',
        store=True,
    )
    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
        index=True,
    )
    parent_id = fields.Many2one(
        comodel_name='planning.batch.explosion.node',
        string='Parent Node',
        ondelete='cascade',
        index=True,
    )
    child_ids = fields.One2many(
        comodel_name='planning.batch.explosion.node',
        inverse_name='parent_id',
        string='Child Nodes',
    )
    parent_path = fields.Char(index=True)
    source_sale_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Source Sales Line',
        readonly=True,
    )
    parent_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Parent Product',
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        readonly=True,
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UoM',
        required=True,
        readonly=True,
    )
    level = fields.Integer(
        string='Level',
        required=True,
        readonly=True,
        index=True,
    )
    demand_qty = fields.Float(
        string='Demand Qty',
        readonly=True,
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
        readonly=True,
    )
    supply_type = fields.Selection(
        [
            ('manufacture', 'Manufacture'),
            ('procure', 'Procure'),
        ],
        string='Supply Type',
        required=True,
        default='procure',
        readonly=True,
        index=True,
    )
    bom_id = fields.Many2one(
        comodel_name='mrp.bom',
        string='BOM',
        readonly=True,
    )
    is_leaf = fields.Boolean(
        string='Leaf',
        readonly=True,
    )
    path_key = fields.Char(
        string='Path',
        readonly=True,
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
        readonly=True,
        index=True,
    )
    message = fields.Char(
        string='Message',
        readonly=True,
    )

    def _compute_name(self):
        for node in self:
            if node.product_id:
                node.name = f"{node.product_id.display_name} ({node.demand_qty:.4f} {node.uom_id.name})"
            else:
                node.name = 'Node'
