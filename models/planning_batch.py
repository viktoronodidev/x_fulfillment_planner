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
    shortage_line_ids = fields.One2many(
        comodel_name='planning.batch.shortage',
        inverse_name='batch_id',
        string='Shortage Lines',
        readonly=True,
    )
    product_summary_ids = fields.One2many(
        comodel_name='planning.batch.product_summary',
        inverse_name='batch_id',
        string='Selected Products',
        compute='_compute_product_summary_ids',
        store=True,
    )
    shortage_count = fields.Integer(
        string='Shortage Count',
        compute='_compute_shortage_count',
        store=True,
    )
    shortage_last_run = fields.Datetime(
        string='Shortage Analyzed At',
        readonly=True,
    )
    shortage_last_run_by = fields.Many2one(
        comodel_name='res.users',
        string='Shortage Analyzed By',
        readonly=True,
    )
    suggested_mo_created_at = fields.Datetime(
        string='Suggested MOs Created At',
        readonly=True,
    )
    suggested_mo_created_by = fields.Many2one(
        comodel_name='res.users',
        string='Suggested MOs Created By',
        readonly=True,
    )
    has_mo = fields.Boolean(
        string='Has MOs',
        compute='_compute_has_mo',
        store=False,
    )

    def action_open_select_sales_orders(self):
        self.ensure_one()
        wizard = self.env['planning.batch.select.so'].create({
            'batch_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Sales Orders'),
            'res_model': 'planning.batch.select.so',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wizard.id,
            'context': {
                'default_batch_id': self.id,
            },
        }

    @api.depends('shortage_line_ids')
    def _compute_shortage_count(self):
        for batch in self:
            batch.shortage_count = len(batch.shortage_line_ids)

    @api.depends('mrp_production_ids')
    def _compute_has_mo(self):
        for batch in self:
            batch.has_mo = bool(batch.mrp_production_ids)

    @api.depends('line_ids.selected', 'line_ids.product_id', 'line_ids.qty_product_uom')
    def _compute_product_summary_ids(self):
        for batch in self:
            summary = {}
            for line in batch.line_ids.filtered('selected'):
                product = line.product_id
                if not product:
                    continue
                summary[product] = summary.get(product, 0.0) + line.qty_product_uom

            values = [(5, 0, 0)]
            for product, qty in summary.items():
                values.append((0, 0, {
                    'product_id': product.id,
                    'uom_id': product.uom_id.id,
                    'qty': qty,
                }))
            batch.product_summary_ids = values

    def action_analyze_shortage(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered('selected')
        if not selected_lines:
            raise UserError(_('Please select at least one Sales Order Line.'))

        self.shortage_line_ids.unlink()

        demand_by_product = {}
        line_ids_by_product = {}
        for line in selected_lines:
            so_line = line.sale_order_line_id
            product = so_line.product_id
            if not product:
                continue
            qty = so_line.product_uom._compute_quantity(
                so_line.product_uom_qty, product.uom_id
            )
            demand_by_product[product] = demand_by_product.get(product, 0.0) + qty
            line_ids_by_product.setdefault(product, set()).add(so_line.id)

        products = list(demand_by_product.keys())
        if not products:
            return

        mo_qty_by_product = {}
        mo_domain = [
            ('product_id', 'in', [p.id for p in products]),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['confirmed', 'progress']),
        ]
        mos = self.env['mrp.production'].search(mo_domain)
        for mo in mos:
            product = mo.product_id
            qty = mo.product_uom_id._compute_quantity(mo.product_qty, product.uom_id)
            mo_qty_by_product[product] = mo_qty_by_product.get(product, 0.0) + qty

        for product, demand_qty in demand_by_product.items():
            on_hand = product.with_company(self.company_id).qty_available
            available_qty = on_hand + mo_qty_by_product.get(product, 0.0)
            shortage_qty = max(demand_qty - available_qty, 0.0)
            self.env['planning.batch.shortage'].create({
                'batch_id': self.id,
                'product_id': product.id,
                'uom_id': product.uom_id.id,
                'demand_qty': demand_qty,
                'available_qty': available_qty,
                'shortage_qty': shortage_qty,
                'source_type': 'so',
                'related_line_ids': [(6, 0, list(line_ids_by_product.get(product, set())))],
            })
        self.shortage_last_run = fields.Datetime.now()
        self.shortage_last_run_by = self.env.user
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shortage analysis completed'),
                'message': _('Shortage table updated.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'planning.batch',
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'res_id': self.id,
                },
            }
        }

    def action_create_suggested_mo(self):
        self.ensure_one()
        shortage_lines = self.shortage_line_ids.filtered(lambda l: l.shortage_qty > 0)
        if not shortage_lines:
            raise UserError(_('No shortages to create Manufacturing Orders.'))

        existing_products = self.mrp_production_ids.mapped('product_id')
        duplicated = shortage_lines.mapped('product_id') & existing_products
        if duplicated:
            names = ', '.join(duplicated.mapped('display_name'))
            raise UserError(_('Manufacturing Order already exists for: %s') % names)

        products = shortage_lines.mapped('product_id')
        bom_map = self._get_bom_map(products)
        missing = [p.display_name for p in products if not bom_map.get(p)]
        if missing:
            raise UserError(_('Missing BOM for: %s') % ', '.join(missing))

        created_mos = self.env['mrp.production']
        for line in shortage_lines:
            product = line.product_id
            bom = bom_map.get(product)
            qty = line.shortage_qty
            if qty <= 0 or not bom:
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

        if created_mos:
            self.mrp_production_ids = [(4, mo.id) for mo in created_mos]
            self.suggested_mo_created_at = fields.Datetime.now()
            self.suggested_mo_created_by = self.env.user
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Suggested MOs created'),
                    'message': _('Manufacturing Orders created for shortages.'),
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window',
                        'res_model': 'planning.batch',
                        'view_mode': 'form',
                        'views': [(False, 'form')],
                        'res_id': self.id,
                    },
                }
            }
        else:
            raise UserError(_('No Manufacturing Orders were created.'))

    def action_undo_created_mo(self):
        self.ensure_one()
        mos = self.mrp_production_ids
        if not mos:
            return
        non_draft = mos.filtered(lambda mo: mo.state != 'draft')
        if non_draft:
            raise UserError(_('Only draft Manufacturing Orders can be removed.'))

        self.line_ids.filtered(lambda l: l.mrp_production_id in mos).write({
            'mrp_production_id': False,
            'status': 'ok',
            'message': False,
        })
        mos.unlink()
        self.mrp_production_ids = [(5, 0, 0)]
        self.suggested_mo_created_at = False
        self.suggested_mo_created_by = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Suggested MOs removed'),
                'message': _('Draft Manufacturing Orders created by this batch were removed.'),
                'type': 'warning',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'planning.batch',
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'res_id': self.id,
                },
            }
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
