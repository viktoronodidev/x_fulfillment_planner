from odoo import fields, models


class PlanningBatchOrder(models.Model):
    _name = 'planning.batch.order'
    _description = 'Planning Batch Order'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
    )
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sales Order',
        required=True,
    )
    partner_id = fields.Many2one(
        related='sale_order_id.partner_id',
        store=True,
        string='Customer',
        readonly=True,
    )
    date_order = fields.Datetime(
        related='sale_order_id.date_order',
        store=True,
        string='Order Date',
        readonly=True,
    )
    state = fields.Selection(
        related='sale_order_id.state',
        store=True,
        string='Status',
        readonly=True,
    )
    amount_total = fields.Monetary(
        related='sale_order_id.amount_total',
        store=True,
        string='Total',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        store=True,
        string='Currency',
        readonly=True,
    )
    sale_order_line_ids = fields.One2many(
        related='sale_order_id.order_line',
        string='Sales Order Lines',
        readonly=True,
    )

    def unlink(self):
        batches = self.mapped('batch_id')
        sale_orders = self.mapped('sale_order_id')
        sale_order_lines = self.env['sale.order.line'].search([
            ('order_id', 'in', sale_orders.ids),
            ('display_type', '=', False),
        ])
        res = super().unlink()
        for batch in batches:
            batch.sale_order_ids = [(3, so.id) for so in sale_orders]
            batch.sale_order_line_ids = [(3, line.id) for line in sale_order_lines]
            batch.line_ids.filtered(lambda l: l.sale_order_line_id in sale_order_lines).unlink()
        return res
