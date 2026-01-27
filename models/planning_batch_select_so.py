from odoo import fields, models, _
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
    sale_order_ids = fields.Many2many(
        comodel_name='sale.order',
        string='Sales Orders',
        domain=[('state', '=', 'sale')],
    )

    def action_select_all(self):
        self.ensure_one()
        domain = [('state', '=', 'sale')]
        if self.batch_id.company_id:
            domain.append(('company_id', '=', self.batch_id.company_id.id))
        orders = self.env['sale.order'].search(domain)
        self.sale_order_ids = [(6, 0, orders.ids)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'planning.batch.select.so',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_apply(self):
        self.ensure_one()
        if not self.sale_order_ids:
            raise UserError(_('Please select at least one Sales Order.'))
        batch = self.batch_id
        batch.sale_order_ids = [(6, 0, self.sale_order_ids.ids)]

        # Sync batch orders
        existing_orders = set(batch.batch_order_ids.mapped('sale_order_id').ids)
        for order in self.sale_order_ids:
            if order.id not in existing_orders:
                self.env['planning.batch.order'].create({
                    'batch_id': batch.id,
                    'sale_order_id': order.id,
                })
        # Remove batch orders not selected
        batch.batch_order_ids.filtered(lambda o: o.sale_order_id not in self.sale_order_ids).unlink()

        # Load all sale order lines for selected orders
        lines = self.env['sale.order.line'].search([
            ('order_id', 'in', self.sale_order_ids.ids),
            ('display_type', '=', False),
        ])
        batch.sale_order_line_ids = [(6, 0, lines.ids)]
        return {'type': 'ir.actions.act_window_close'}
