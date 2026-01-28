from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PlanningBatchSelectSO(models.TransientModel):
    _name = 'planning.batch.select.so'
    _description = 'Select Sales Orders'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
    )
    search_text = fields.Char(string='Search')
    line_ids = fields.One2many(
        comodel_name='planning.batch.select.so.line',
        inverse_name='wizard_id',
        string='Sales Orders',
    )
    product_line_ids = fields.One2many(
        comodel_name='planning.batch.select.so.product',
        inverse_name='wizard_id',
        string='Product Summary',
        compute='_compute_product_lines',
    )
    has_product_summary = fields.Boolean(
        string='Has Product Summary',
        compute='_compute_product_lines',
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for wizard in records:
            if not wizard.line_ids:
                wizard._reload_lines()
        return records

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        batch_id = self.env.context.get('default_batch_id')
        if not batch_id:
            return res
        batch = self.env['planning.batch'].browse(batch_id)
        domain = [('state', '=', 'sale')]
        if batch.company_id:
            domain.append(('company_id', '=', batch.company_id.id))
        orders = self.env['sale.order'].search(domain, order='date_order desc')
        res['line_ids'] = [
            (0, 0, {
                'sale_order_id': order.id,
                'selected': order.id in batch.sale_order_ids.ids,
            }) for order in orders
        ]
        return res

    def _get_domain(self):
        domain = [('state', '=', 'sale')]
        if self.batch_id.company_id:
            domain.append(('company_id', '=', self.batch_id.company_id.id))
        if self.search_text:
            term = self.search_text.strip()
            if term:
                domain += ['|', ('name', 'ilike', term), ('partner_id.name', 'ilike', term)]
        return domain

    def _reload_lines(self):
        self.ensure_one()
        selected_ids = set(self.line_ids.filtered('selected').mapped('sale_order_id').ids)
        orders = self.env['sale.order'].search(self._get_domain(), order='date_order desc')
        self.line_ids = [(5, 0, 0)]
        self.line_ids = [
            (0, 0, {
                'sale_order_id': order.id,
                'selected': order.id in selected_ids,
            }) for order in orders
        ]

    @api.depends('line_ids', 'line_ids.selected', 'line_ids.sale_order_id')
    def _compute_product_lines(self):
        for wizard in self:
            wizard._set_product_lines()
            wizard.has_product_summary = bool(wizard.product_line_ids)

    def _set_product_lines(self):
        self.ensure_one()
        self.product_line_ids = [(5, 0, 0)]
        selected_orders = self.line_ids.filtered('selected').mapped('sale_order_id')
        if not selected_orders:
            self.has_product_summary = False
            return
        order_lines = self.env['sale.order.line'].search([
            ('order_id', 'in', selected_orders.ids),
            ('display_type', '=', False),
        ])
        qty_by_product = {}
        for line in order_lines:
            product = line.product_id
            if not product:
                continue
            qty_by_product.setdefault(product, 0.0)
            qty_by_product[product] += line.product_uom_qty
        self.product_line_ids = [
            (0, 0, {
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'qty': qty,
            }) for product, qty in qty_by_product.items()
        ]
        self.has_product_summary = bool(self.product_line_ids)

    def action_search(self):
        self.ensure_one()
        self._reload_lines()
        self._set_product_lines()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'planning.batch.select.so',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_select_all(self):
        self.ensure_one()
        for line in self.line_ids:
            line.selected = True
        self._set_product_lines()
        return self.action_search()

    def action_deselect_all(self):
        self.ensure_one()
        for line in self.line_ids:
            line.selected = False
        self._set_product_lines()
        return self.action_search()

    @api.onchange('line_ids', 'line_ids.selected')
    def _onchange_line_ids_selected(self):
        for wizard in self:
            wizard._set_product_lines()

    def action_apply(self):
        self.ensure_one()
        selected_orders = self.line_ids.filtered('selected').mapped('sale_order_id')
        if not selected_orders:
            raise UserError(_('Please select at least one Sales Order.'))

        batch = self.batch_id
        batch.sale_order_ids = [(6, 0, selected_orders.ids)]

        # Sync batch orders
        existing_orders = set(batch.batch_order_ids.mapped('sale_order_id').ids)
        for order in selected_orders:
            if order.id not in existing_orders:
                self.env['planning.batch.order'].create({
                    'batch_id': batch.id,
                    'sale_order_id': order.id,
                })
        batch.batch_order_ids.filtered(lambda o: o.sale_order_id not in selected_orders).unlink()

        # Sync batch lines for selected orders
        existing_lines = {line.sale_order_line_id.id: line for line in batch.line_ids}
        order_lines = self.env['sale.order.line'].search([
            ('order_id', 'in', selected_orders.ids),
            ('display_type', '=', False),
        ])
        for line in order_lines:
            if line.id not in existing_lines:
                batch_order = batch.batch_order_ids.filtered(lambda o: o.sale_order_id == line.order_id)
                if batch_order:
                    self.env['planning.batch.line'].create({
                        'batch_id': batch.id,
                        'batch_order_id': batch_order.id,
                        'sale_order_line_id': line.id,
                        'selected': True,
                    })
        # Remove batch lines for removed orders
        batch.line_ids.filtered(lambda l: l.sale_order_id not in selected_orders).unlink()

        return {'type': 'ir.actions.act_window_close'}
