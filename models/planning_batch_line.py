from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PlanningBatchLine(models.Model):
    _name = 'planning.batch.line'
    _description = 'Planning Batch Line'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
    )
    batch_order_id = fields.Many2one(
        comodel_name='planning.batch.order',
        string='Batch Order',
        required=True,
        ondelete='cascade',
    )
    selected = fields.Boolean(string='Select', default=True)
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
    )
    message = fields.Char(string='Message')
    mrp_production_id = fields.Many2one(
        comodel_name='mrp.production',
        string='Manufacturing Order',
        readonly=True,
    )

    @api.depends('product_uom_qty', 'product_uom', 'product_id')
    def _compute_qty_product_uom(self):
        for line in self:
            product = line.product_id
            if not product or not line.product_uom:
                line.qty_product_uom = 0.0
                continue
            line.qty_product_uom = line.product_uom._compute_quantity(
                line.product_uom_qty, product.uom_id
            )

    def unlink(self):
        batches = self.mapped('batch_id')
        for batch in batches:
            if batch.mrp_production_ids:
                raise UserError(_('You cannot remove Sales Order Lines while Manufacturing Orders exist for this batch.'))
        res = super().unlink()
        for batch in batches:
            for order in batch.batch_order_ids:
                if not order.batch_line_ids:
                    order.unlink()
            batch.shortage_line_ids.unlink()
            batch.shortage_last_run = False
            batch.shortage_last_run_by = False
        return res
