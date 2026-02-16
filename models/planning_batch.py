from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta


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
            ('shortage_analyzed', 'Shortage Analyzed'),
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
    bom_missing_ids = fields.One2many(
        comodel_name='planning.batch.bom_issue',
        inverse_name='batch_id',
        string='Products without BOM',
        compute='_compute_bom_missing_ids',
        store=True,
    )
    sales_order_count = fields.Integer(
        string='Sales Orders Included',
        compute='_compute_sales_order_count',
        store=True,
    )
    product_count = fields.Integer(
        string='Products Included',
        compute='_compute_product_count',
        store=True,
    )
    bom_missing_count = fields.Integer(
        string='Products without BOM',
        compute='_compute_bom_missing_ids',
        store=True,
    )
    shortage_count = fields.Integer(
        string='Shortage Count',
        compute='_compute_shortage_count',
        store=True,
    )
    shortage_qty_total = fields.Float(
        string='Total Shortage Qty',
        compute='_compute_shortage_qty_total',
        store=True,
    )
    uncovered_demand_qty = fields.Float(
        string='Uncovered Demand Qty',
        compute='_compute_coverage_metrics',
        store=True,
    )
    mo_coverage_pct = fields.Float(
        string='MO Coverage %',
        compute='_compute_coverage_metrics',
        store=True,
    )
    mo_created_count = fields.Integer(
        string='MOs Created',
        compute='_compute_mo_created_count',
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
        string='MOs Created At',
        readonly=True,
    )
    suggested_mo_created_by = fields.Many2one(
        comodel_name='res.users',
        string='MOs Created By',
        readonly=True,
    )

    @api.constrains('status', 'company_id')
    def _check_single_draft_per_company(self):
        for batch in self:
            if batch.status != 'draft':
                continue
            domain = [
                ('id', '!=', batch.id),
                ('status', '=', 'draft'),
                ('company_id', '=', batch.company_id.id),
            ]
            if self.search_count(domain):
                raise UserError(_('Only one Draft Planning Batch is allowed per company.'))

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

    @api.depends('shortage_line_ids.shortage_qty')
    def _compute_shortage_qty_total(self):
        for batch in self:
            batch.shortage_qty_total = sum(batch.shortage_line_ids.mapped('shortage_qty'))

    @api.depends('mrp_production_ids')
    def _compute_mo_created_count(self):
        for batch in self:
            batch.mo_created_count = len(batch.mrp_production_ids)

    @api.depends('batch_order_ids')
    def _compute_sales_order_count(self):
        for batch in self:
            batch.sales_order_count = len(batch.batch_order_ids)

    @api.depends('line_ids', 'line_ids.selected', 'line_ids.product_id')
    def _compute_product_count(self):
        for batch in self:
            products = batch.line_ids.filtered('selected').mapped('product_id')
            batch.product_count = len(products)

    @api.depends('line_ids', 'line_ids.selected', 'line_ids.product_id')
    def _compute_bom_missing_ids(self):
        for batch in self:
            selected_products = batch.line_ids.filtered('selected').mapped('product_id')
            values = [(5, 0, 0)]
            missing = []
            if selected_products:
                bom_map = batch._get_bom_map(selected_products)
                missing = [p for p in selected_products if not bom_map.get(p)]
                for product in missing:
                    values.append((0, 0, {
                        'product_id': product.id,
                        'uom_id': product.uom_id.id,
                    }))
            batch.bom_missing_ids = values
            batch.bom_missing_count = len(missing)

    @api.depends('line_ids', 'line_ids.selected', 'line_ids.qty_product_uom', 'shortage_line_ids.shortage_qty')
    def _compute_coverage_metrics(self):
        for batch in self:
            selected_lines = batch.line_ids.filtered('selected')
            demand_total = sum(selected_lines.mapped('qty_product_uom'))
            shortage_total = sum(batch.shortage_line_ids.mapped('shortage_qty'))
            batch.uncovered_demand_qty = shortage_total
            if demand_total:
                batch.mo_coverage_pct = (max(demand_total - shortage_total, 0.0) / demand_total) * 100.0
            else:
                batch.mo_coverage_pct = 0.0

    @api.depends('line_ids', 'line_ids.selected', 'line_ids.product_id', 'line_ids.qty_product_uom')
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

    def _clear_shortage_data(self):
        self.shortage_line_ids.unlink()
        self.shortage_last_run = False
        self.shortage_last_run_by = False

    def _reset_to_draft(self):
        self._clear_shortage_data()
        self.status = 'draft'

    def _reset_shortage_on_sales_change(self):
        for batch in self:
            batch._clear_shortage_data()
            if batch.status == 'shortage_analyzed':
                batch.status = 'draft'

    def _reset_stale_shortage(self):
        now = fields.Datetime.now()
        cutoff = now - timedelta(minutes=30)
        stale_batches = self.filtered(
            lambda b: b.status == 'shortage_analyzed'
            and b.shortage_last_run
            and b.shortage_last_run <= cutoff
        )
        for batch in stale_batches:
            batch._reset_to_draft()

    def read(self, fields=None, load='_classic_read'):
        self._reset_stale_shortage()
        return super().read(fields=fields, load=load)

    def action_analyze_shortage(self):
        self.ensure_one()
        if self.status not in ['draft', 'shortage_analyzed']:
            raise UserError(_('Shortage analysis can only be run in Draft or Shortage Analyzed status.'))
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
        self.status = 'shortage_analyzed'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shortage analysis completed'),
                'message': _('Shortage table updated.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            }
        }

    def action_create_suggested_mo(self):
        self.ensure_one()
        if self.status != 'shortage_analyzed':
            raise UserError(_('Create MOs is only available after Shortage Analysis.'))
        shortage_lines = self.shortage_line_ids.filtered(lambda l: l.shortage_qty > 0)
        if not shortage_lines:
            raise UserError(_('No shortages to create Manufacturing Orders.'))

        existing_products = self.mrp_production_ids.mapped('product_id')
        duplicated = shortage_lines.mapped('product_id') & existing_products
        if duplicated:
            raise UserError(_('Manufacturing orders already exist for all selected products.'))

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
            self.status = 'calculated'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('MOs created'),
                    'message': _('Manufacturing Orders created for shortages.'),
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'soft_reload',
                    },
                }
            }
        else:
            raise UserError(_('No Manufacturing Orders were created.'))

    def action_undo_created_mo(self):
        self.ensure_one()
        mos = self.mrp_production_ids
        if not mos:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Manufacturing Orders'),
                    'message': _('There are no draft MOs to remove.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
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
                    'title': _('MOs removed'),
                    'message': _('Draft Manufacturing Orders created by this batch were removed.'),
                    'type': 'warning',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'soft_reload',
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
