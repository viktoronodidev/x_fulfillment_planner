from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PlanningBatch(models.Model):
    _name = 'planning.batch'
    _description = 'Planning Batch'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('planning.batch') or 'New',
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('calculated', 'Calculated'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done'),
        ],
        string='Status',
        required=True,
        default='draft',
    )
    note = fields.Text(string='Note')
    sale_order_ids = fields.Many2many(
        comodel_name='sale.order',
        relation='planning_batch_sale_order_rel',
        column1='planning_batch_id',
        column2='sale_order_id',
        string='Sales Orders',
        domain=[('state', '=', 'sale')],
    )
    batch_order_ids = fields.One2many(
        comodel_name='planning.batch.order',
        inverse_name='batch_id',
        string='Selected Sales Orders',
    )
    line_ids = fields.One2many(
        comodel_name='planning.batch.line',
        inverse_name='batch_id',
        string='Batch Lines',
    )
    mrp_production_ids = fields.Many2many(
        comodel_name='mrp.production',
        relation='planning_batch_mrp_production_rel',
        column1='planning_batch_id',
        column2='mrp_production_id',
        string='Manufacturing Orders',
        readonly=True,
    )
    mo_line_ids = fields.Many2many(
        comodel_name='stock.move',
        relation='planning_batch_mo_line_rel',
        column1='planning_batch_id',
        column2='stock_move_id',
        string='Manufacturing Order Lines',
        readonly=True,
        domain=[('raw_material_production_id', '!=', False)],
    )
    purchase_order_ids = fields.Many2many(
        comodel_name='purchase.order',
        relation='planning_batch_purchase_order_rel',
        column1='planning_batch_id',
        column2='purchase_order_id',
        string='Purchase Orders',
        readonly=True,
    )
    purchase_order_line_ids = fields.Many2many(
        comodel_name='purchase.order.line',
        relation='planning_batch_purchase_order_line_rel',
        column1='planning_batch_id',
        column2='purchase_order_line_id',
        string='Purchase Order Lines',
        readonly=True,
    )

    def action_open_select_sales_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Sales Orders'),
            'res_model': 'planning.batch.select.so',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_batch_id': self.id,
            },
        }

    def _get_bom_map(self, products):
        if not products:
            return {}
        bom_map = self.env['mrp.bom']._bom_find(
            products,
            company_id=self.company_id.id,
        )
        return bom_map

    def action_calculate(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered('selected')
        if not selected_lines:
            raise UserError(_('Please select at least one Sales Order Line.'))

        company_ids = selected_lines.mapped('sale_order_id.company_id')
        if len(company_ids) > 1:
            raise UserError(_('Please select Sales Order Lines from a single company.'))

        products = selected_lines.mapped('product_id')
        bom_map = self._get_bom_map(products)

        for batch_line in selected_lines:
            batch_line.status = 'ok'
            batch_line.message = False
            product = batch_line.product_id
            if not product:
                batch_line.status = 'failed'
                batch_line.message = _('Missing product on sales order line.')
                continue
            if product.type != 'product':
                batch_line.status = 'failed'
                batch_line.message = _('Product is not storable (type must be Storable Product).')
                continue
            bom = bom_map.get(product)
            if not bom:
                batch_line.status = 'failed'
                batch_line.message = _('No Bill of Materials found for product.')
                continue

        self.status = 'calculated'

    def action_create_mo(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered('selected')
        if not selected_lines:
            raise UserError(_('Please select at least one Sales Order Line.'))

        ok_lines = selected_lines.filtered(lambda l: l.status == 'ok')
        already_linked = ok_lines.filtered(lambda l: l.mrp_production_id)
        if already_linked:
            for line in already_linked:
                line.status = 'failed'
                line.message = _('MO already created for this line.')
        ok_lines = ok_lines.filtered(lambda l: not l.mrp_production_id)
        if not ok_lines:
            raise UserError(_('No valid lines to create Manufacturing Orders.'))

        products = ok_lines.mapped('product_id')
        bom_map = self._get_bom_map(products)

        qty_by_product = {}
        lines_by_product = {}
        for line in ok_lines:
            product = line.product_id
            qty_by_product[product] = qty_by_product.get(product, 0.0) + line.qty_product_uom
            lines_by_product.setdefault(product, []).append(line)

        created_mos = self.env['mrp.production']
        for product, qty in qty_by_product.items():
            if qty <= 0:
                for line in lines_by_product.get(product, []):
                    line.status = 'failed'
                    line.message = _('Quantity is zero after conversion.')
                continue
            bom = bom_map.get(product)
            if not bom:
                for line in lines_by_product.get(product, []):
                    line.status = 'failed'
                    line.message = _('No Bill of Materials found for product.')
                continue

            mo_vals = {
                'product_id': product.id,
                'product_qty': qty,
                'product_uom_id': product.uom_id.id,
                'bom_id': bom.id,
                'origin': self.name,
            }
            mo = self.env['mrp.production'].create(mo_vals)
            created_mos |= mo
            for line in lines_by_product.get(product, []):
                line.mrp_production_id = mo.id

        if created_mos:
            self.mrp_production_ids = [(4, mo.id) for mo in created_mos]
            self.status = 'confirmed'
        else:
            raise UserError(_('No Manufacturing Orders were created.'))
