from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProcurementBatch(models.Model):
    _name = 'procurement.batch'
    _description = 'Procurement Planner Batch'
    _order = 'id desc'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('procurement.batch') or 'New',
    )
    date = fields.Date(string='Date', default=fields.Date.context_today)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    note = fields.Text(string='Note')
    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('analyzed', 'Analyzed'),
            ('rfq_created', 'RFQ Created'),
            ('done', 'Done'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    include_open_demands = fields.Boolean(string='Open Demands', default=True)
    include_min_stock = fields.Boolean(string='Minimum Stock Quantities', default=True)
    show_all_open_rfqs = fields.Boolean(string='Show All Open RFQs', default=False)

    line_ids = fields.One2many(
        comodel_name='procurement.batch.line',
        inverse_name='batch_id',
        string='Procurement Analysis',
        copy=False,
    )

    created_rfq_ids = fields.Many2many(
        comodel_name='purchase.order',
        relation='procurement_batch_purchase_order_rel',
        column1='procurement_batch_id',
        column2='purchase_order_id',
        string='Run-Created RFQs',
        copy=False,
    )

    rfq_ids = fields.Many2many(
        comodel_name='purchase.order',
        string='RFQs',
        compute='_compute_rfq_ids',
        readonly=True,
    )

    analysis_run_at = fields.Datetime(string='Last Analyzed At', readonly=True)
    analysis_run_by = fields.Many2one(
        comodel_name='res.users',
        string='Last Analyzed By',
        readonly=True,
    )

    product_count = fields.Integer(string='Products', compute='_compute_kpis', readonly=True)
    ready_count = fields.Integer(string='Ready Lines', compute='_compute_kpis', readonly=True)
    missing_vendor_count = fields.Integer(string='Missing Vendor', compute='_compute_kpis', readonly=True)
    suggested_qty_total = fields.Float(string='Suggested Qty', compute='_compute_kpis', readonly=True)
    rfq_count = fields.Integer(string='RFQs', compute='_compute_kpis', readonly=True)

    @api.depends('show_all_open_rfqs', 'created_rfq_ids', 'company_id')
    def _compute_rfq_ids(self):
        for batch in self:
            if batch.show_all_open_rfqs:
                batch.rfq_ids = self.env['purchase.order'].search([
                    ('company_id', '=', batch.company_id.id),
                    ('state', 'in', ['draft', 'sent', 'to approve', 'purchase']),
                ])
            else:
                batch.rfq_ids = batch.created_rfq_ids

    @api.depends('line_ids.status', 'line_ids.suggested_qty', 'rfq_ids')
    def _compute_kpis(self):
        for batch in self:
            lines = batch.line_ids
            batch.product_count = len(lines)
            batch.ready_count = len(lines.filtered(lambda l: l.status == 'ready' and l.suggested_qty > 0))
            batch.missing_vendor_count = len(lines.filtered(lambda l: l.status == 'missing_vendor'))
            batch.suggested_qty_total = sum(lines.mapped('suggested_qty'))
            batch.rfq_count = len(batch.rfq_ids)

    def _get_global_open_procurement_demand(self):
        self.ensure_one()
        demands = defaultdict(float)
        move_domain = [
            ('company_id', '=', self.company_id.id),
            ('state', 'not in', ['done', 'cancel']),
            ('raw_material_production_id', '!=', False),
        ]
        for move in self.env['stock.move'].search(move_domain):
            product = move.product_id
            if not product or product.type == 'service':
                continue
            remaining = max(move.product_uom_qty - move.quantity_done, 0.0)
            if remaining <= 0:
                continue
            qty = move.product_uom._compute_quantity(remaining, product.uom_id)
            demands[product.id] += qty
        return demands

    def _get_open_procurement_qty(self, products):
        self.ensure_one()
        qty_by_product = defaultdict(float)
        domain = [
            ('order_id.company_id', '=', self.company_id.id),
            ('order_id.state', 'in', ['draft', 'sent', 'to approve', 'purchase']),
            ('product_id', 'in', products.ids),
            ('display_type', '=', False),
        ]
        for line in self.env['purchase.order.line'].search(domain):
            qty = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            qty_by_product[line.product_id.id] += qty
        return qty_by_product

    def _get_min_stock_targets(self, products):
        self.ensure_one()
        min_by_product = defaultdict(float)
        domain = [
            ('company_id', '=', self.company_id.id),
            ('product_id', 'in', products.ids),
        ]
        for op in self.env['stock.warehouse.orderpoint'].search(domain):
            qty = op.product_uom._compute_quantity(op.product_min_qty, op.product_id.uom_id)
            min_by_product[op.product_id.id] += qty
        return min_by_product

    def _pick_vendor(self, product):
        sellers = product.seller_ids.filtered(lambda s: not s.company_id or s.company_id == self.company_id)
        sellers = sellers.sorted(lambda s: (s.sequence, s.id))
        return sellers[:1].partner_id

    def action_analyze(self):
        self.ensure_one()
        if not self.include_open_demands and not self.include_min_stock:
            raise UserError(_('At least one demand source must be enabled.'))

        products = self.env['product.product']

        open_demand_by_product = defaultdict(float)
        if self.include_open_demands:
            open_demand_by_product = self._get_global_open_procurement_demand()
            products |= self.env['product.product'].browse(list(open_demand_by_product.keys()))

        min_target_by_product = defaultdict(float)
        if self.include_min_stock:
            orderpoint_products = self.env['stock.warehouse.orderpoint'].search([
                ('company_id', '=', self.company_id.id),
            ]).mapped('product_id')
            products |= orderpoint_products
            min_target_by_product = self._get_min_stock_targets(products)

        self.line_ids.unlink()

        if not products:
            self.status = 'analyzed'
            self.analysis_run_at = fields.Datetime.now()
            self.analysis_run_by = self.env.user
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No procurement demand'),
                    'message': _('No products found for selected scope.'),
                    'type': 'info',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
                }
            }

        open_proc_qty = self._get_open_procurement_qty(products)

        create_vals = []
        for product in products.sorted('display_name'):
            if product.type == 'service':
                continue

            open_demand = open_demand_by_product.get(product.id, 0.0) if self.include_open_demands else 0.0
            min_target = min_target_by_product.get(product.id, 0.0) if self.include_min_stock else 0.0
            available = product.with_company(self.company_id).qty_available
            existing_open_qty = open_proc_qty.get(product.id, 0.0)

            total_target_qty = open_demand + min_target
            uncovered_qty = max(total_target_qty - available, 0.0)
            suggested = max(uncovered_qty - existing_open_qty, 0.0)

            vendor = self._pick_vendor(product)
            status = 'no_demand'
            message = _('No action needed')
            if suggested > 0 and not vendor:
                status = 'missing_vendor'
                message = _('Missing vendor on product')
            elif suggested > 0:
                status = 'ready'
                message = False

            create_vals.append({
                'batch_id': self.id,
                'product_id': product.id,
                'uom_id': product.uom_id.id,
                'vendor_id': vendor.id if vendor else False,
                'open_demand_qty': open_demand,
                'min_stock_target_qty': min_target,
                'total_target_qty': total_target_qty,
                'available_qty': available,
                'uncovered_qty': uncovered_qty,
                'existing_open_rfq_qty': existing_open_qty,
                'suggested_qty': suggested,
                'status': status,
                'message': message,
            })

        if create_vals:
            self.env['procurement.batch.line'].create(create_vals)

        self.status = 'analyzed'
        self.analysis_run_at = fields.Datetime.now()
        self.analysis_run_by = self.env.user

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Procurement analysis completed'),
                'message': _('Procurement suggestions are ready for review.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }

    def _get_or_create_vendor_rfq(self, vendor):
        self.ensure_one()
        draft_domain = [
            ('company_id', '=', self.company_id.id),
            ('partner_id', '=', vendor.id),
            ('state', '=', 'draft'),
        ]
        draft_rfqs = self.env['purchase.order'].search(draft_domain)
        if len(draft_rfqs) > 1:
            raise UserError(_('Only one Draft RFQ is allowed per vendor and company.'))
        if draft_rfqs:
            return draft_rfqs[0]
        return self.env['purchase.order'].create({
            'partner_id': vendor.id,
            'company_id': self.company_id.id,
            'origin': f"PP:{self.name}",
        })

    def action_create_rfqs(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda l: l.suggested_qty > 0)
        if not lines:
            raise UserError(_('No procurement suggestions with quantity to buy.'))

        missing_vendor = lines.filtered(lambda l: not l.vendor_id)
        if missing_vendor:
            raise UserError(_('Some lines are missing vendor setup. Fix vendors before creating RFQs.'))

        created_pos = self.env['purchase.order']
        created_lines = self.env['purchase.order.line']

        for vendor in lines.mapped('vendor_id'):
            rfq = self._get_or_create_vendor_rfq(vendor)
            created_pos |= rfq
            vendor_lines = lines.filtered(lambda l: l.vendor_id == vendor)
            for line in vendor_lines:
                open_qty = self._get_open_procurement_qty(line.product_id).get(line.product_id.id, 0.0)
                remaining = max(line.uncovered_qty - open_qty, 0.0)
                if remaining <= 0:
                    continue

                qty_po_uom = line.product_id.uom_id._compute_quantity(remaining, line.product_id.uom_po_id)
                qty_po_uom = line.product_id.uom_po_id._compute_quantity(
                    qty_po_uom,
                    line.product_id.uom_po_id,
                    rounding_method='UP',
                )

                pol = self.env['purchase.order.line'].create({
                    'order_id': rfq.id,
                    'product_id': line.product_id.id,
                    'product_qty': qty_po_uom,
                    'product_uom': line.product_id.uom_po_id.id,
                    'price_unit': line.product_id.standard_price,
                    'name': line.product_id.display_name,
                    'date_planned': fields.Datetime.now(),
                })
                created_lines |= pol

        if not created_lines:
            raise UserError(_('No RFQ lines were created (already covered by open RFQs/POs).'))

        self.created_rfq_ids = [(4, po.id) for po in created_pos]
        self.status = 'rfq_created'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('RFQs created'),
                'message': _('Draft RFQs are ready for review.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }

    def action_set_done(self):
        self.write({'status': 'done'})

    def action_set_draft(self):
        self.write({'status': 'draft'})
