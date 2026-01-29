from odoo import fields, models
from odoo import _


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
    batch_line_ids = fields.One2many(
        comodel_name='planning.batch.line',
        inverse_name='batch_order_id',
        string='Sales Order Lines',
    )

    def unlink(self):
        batches = self.mapped('batch_id')
        orders = self.mapped('sale_order_id')
        for batch in batches:
            batch.line_ids.filtered(lambda l: l.sale_order_id in orders).unlink()
        res = super().unlink()
        for batch in batches:
            batch.sale_order_ids = [(3, so.id) for so in orders]
            if not batch.batch_order_ids:
                batch.sale_order_ids = [(5, 0, 0)]
        return res

    def action_remove_from_batch(self):
        self.ensure_one()
        batch = self.batch_id
        self.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'soft_reload',
        }
