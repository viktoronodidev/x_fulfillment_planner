from odoo import api, fields, models


class PlanningBatchSelectSOLine(models.TransientModel):
    _name = 'planning.batch.select.so.line'
    _description = 'Select Sales Orders Line'

    wizard_id = fields.Many2one(
        comodel_name='planning.batch.select.so',
        string='Wizard',
        required=False,
        ondelete='cascade',
    )
    selected = fields.Boolean(string='Select')
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
    amount_total = fields.Monetary(
        related='sale_order_id.amount_total',
        store=True,
        string='Total',
        readonly=True,
    )
    state = fields.Selection(
        related='sale_order_id.state',
        store=True,
        string='Status',
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

    @api.onchange('selected')
    def _onchange_selected(self):
        for line in self:
            if line.wizard_id:
                line.wizard_id._set_product_lines()
