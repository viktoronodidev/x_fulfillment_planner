from odoo import fields, models


class PlanningBatchLine(models.Model):
    _name = 'planning.batch.line'
    _description = 'Planning Batch Line'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
    )
    sale_order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Sales Order Line',
        required=True,
    )
    sale_order_id = fields.Many2one(
        related='sale_order_line_id.order_id',
        store=True,
        string='Sales Order',
        readonly=True,
    )
    product_id = fields.Many2one(
        related='sale_order_line_id.product_id',
        store=True,
        string='Product',
        readonly=True,
    )
    product_uom = fields.Many2one(
        related='sale_order_line_id.product_uom',
        store=True,
        string='UoM',
        readonly=True,
    )
    product_uom_qty = fields.Float(
        related='sale_order_line_id.product_uom_qty',
        store=True,
        string='Qty (SO UoM)',
        readonly=True,
    )
    qty_product_uom = fields.Float(
        string='Qty (Product UoM)',
        compute='_compute_qty_product_uom',
        store=True,
        readonly=True,
    )
    status = fields.Selection(
        [
            ('ok', 'OK'),
            ('failed', 'Failed'),
        ],
        string='Status',
        default='ok',
        required=True,
    )
    message = fields.Char(string='Message')
    mrp_production_id = fields.Many2one(
        comodel_name='mrp.production',
        string='Manufacturing Order',
        readonly=True,
    )

    def _compute_qty_product_uom(self):
        for line in self:
            product = line.product_id
            if not product or not line.product_uom:
                line.qty_product_uom = 0.0
                continue
            line.qty_product_uom = line.product_uom._compute_quantity(
                line.product_uom_qty, product.uom_id
            )
