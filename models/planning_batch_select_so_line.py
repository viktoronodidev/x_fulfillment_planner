from odoo import fields, models


class PlanningBatchSelectSOLine(models.TransientModel):
    _name = 'planning.batch.select.so.line'
    _description = 'Select Sales Orders Line'

    wizard_id = fields.Many2one(
        comodel_name='planning.batch.select.so',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sales Order',
        required=True,
    )
    selected = fields.Boolean(string='Selected')
    selection_state = fields.Selection(
        [
            ('selected', 'Selected'),
            ('not_selected', 'Not selected'),
        ],
        string='Status',
        compute='_compute_selection_state',
        store=True,
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

    def _compute_selection_state(self):
        for line in self:
            line.selection_state = 'selected' if line.selected else 'not_selected'

    def action_select(self):
        for line in self:
            line.selected = True
            if line.wizard_id:
                line.wizard_id._refresh_summary()

    def action_deselect(self):
        for line in self:
            line.selected = False
            if line.wizard_id:
                line.wizard_id._refresh_summary()
