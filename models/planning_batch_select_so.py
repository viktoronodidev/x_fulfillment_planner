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
    )
    has_product_summary = fields.Boolean(
        string='Has Product Summary',
        compute='_compute_has_product_summary',
    )

    def _get_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'planning.batch.select.so',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for wizard in records:
            wizard._reload_lines()
            wizard._refresh_summary()
        return records

    @api.depends('product_line_ids')
    def _compute_has_product_summary(self):
        for wizard in self:
            wizard.has_product_summary = bool(wizard.product_line_ids)

    def _get_domain(self):
        domain = [('state', '=', 'sale')]
        if self.batch_id.company_id:
            domain.append(('company_id', '=', self.batch_id.company_id.id))
        if self.batch_id:
            locked_orders = self.env['planning.batch'].search([
                ('id', '!=', self.batch_id.id),
            ]).mapped('sale_order_ids')
            if locked_orders:
                domain.append(('id', 'not in', locked_orders.ids))
        if self.search_text:
            term = self.search_text.strip()
            if term:
                domain += ['|', ('name', 'ilike', term), ('partner_id.name', 'ilike', term)]
        return domain

    def _reload_lines(self):
        self.ensure_one()
        orders = self.env['sale.order'].search(self._get_domain(), order='date_order desc')
        existing_by_so = {line.sale_order_id.id: line for line in self.line_ids}
        keep_ids = set()
        for order in orders:
            if order.id in existing_by_so:
                keep_ids.add(existing_by_so[order.id].id)
                continue
            self.env['planning.batch.select.so.line'].create({
                'wizard_id': self.id,
                'sale_order_id': order.id,
                'selected': order.id in self.batch_id.sale_order_ids.ids,
            })
        self.line_ids.filtered(lambda l: l.id not in keep_ids and l.sale_order_id not in orders).unlink()

    def _refresh_summary(self):
        self.ensure_one()
        self.product_line_ids.unlink()
        selected_lines = self.env['planning.batch.select.so.line'].search([
            ('wizard_id', '=', self.id),
            ('selected', '=', True),
        ])
        selected_orders = selected_lines.mapped('sale_order_id')
        if not selected_orders:
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
            qty_by_product[product] += line.product_uom._compute_quantity(
                line.product_uom_qty, product.uom_id
            )
        for product, qty in qty_by_product.items():
            self.env['planning.batch.select.so.product'].create({
                'wizard_id': self.id,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'qty': qty,
            })

    def action_search(self):
        self.ensure_one()
        self._reload_lines()
        self._refresh_summary()
        return self._get_action()

    def action_select_all(self):
        self.ensure_one()
        self.line_ids.write({'selected': True})
        self._refresh_summary()
        return self._get_action()

    def action_deselect_all(self):
        self.ensure_one()
        self.line_ids.write({'selected': False})
        self._refresh_summary()
        return self._get_action()

    def action_apply(self):
        self.ensure_one()
        selected_orders = self.line_ids.filtered('selected').mapped('sale_order_id')
        if not selected_orders:
            raise UserError(_('Please select at least one Sales Order.'))

        batch = self.batch_id
        # Reset selections and rebuild from scratch
        batch.line_ids.unlink()
        batch.batch_order_ids.unlink()
        batch.sale_order_ids = [(6, 0, selected_orders.ids)]

        for order in selected_orders:
            self.env['planning.batch.order'].create({
                'batch_id': batch.id,
                'sale_order_id': order.id,
            })

        order_lines = self.env['sale.order.line'].search([
            ('order_id', 'in', selected_orders.ids),
            ('display_type', '=', False),
        ])
        for line in order_lines:
            batch_order = batch.batch_order_ids.filtered(lambda o: o.sale_order_id == line.order_id)
            if batch_order:
                self.env['planning.batch.line'].create({
                    'batch_id': batch.id,
                    'batch_order_id': batch_order.id,
                    'sale_order_line_id': line.id,
                    'selected': True,
                })
        batch._reset_shortage_on_sales_change()

        return {'type': 'ir.actions.act_window_close'}
