from collections import defaultdict
from datetime import timedelta

from lxml import etree

from odoo import _, api, fields, models
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
    explosion_node_ids = fields.One2many(
        comodel_name='planning.batch.explosion.node',
        inverse_name='batch_id',
        string='Explosion Nodes',
        readonly=True,
    )
    demand_summary_ids = fields.One2many(
        comodel_name='planning.batch.demand.summary',
        inverse_name='batch_id',
        string='Demand Summary',
        readonly=True,
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
    semi_product_count = fields.Integer(
        string='Semi Products',
        compute='_compute_explosion_metrics',
        store=True,
    )
    raw_product_count = fields.Integer(
        string='Raw Products',
        compute='_compute_explosion_metrics',
        store=True,
    )
    explosion_issue_count = fields.Integer(
        string='Explosion Issues',
        compute='_compute_explosion_metrics',
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
    explosion_last_run = fields.Datetime(
        string='Structure Analyzed At',
        readonly=True,
    )
    explosion_last_run_by = fields.Many2one(
        comodel_name='res.users',
        string='Structure Analyzed By',
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

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'tree':
            has_draft = self.search_count([
                ('status', '=', 'draft'),
                ('company_id', '=', self.env.company.id),
            ])
            if has_draft:
                doc = etree.XML(result['arch'])
                doc.set('create', 'false')
                result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

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

    def action_open_manufacturing_chain(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Manufacturing Chain'),
            'res_model': 'planning.batch.explosion.node',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('x_fulfillment_planner.view_planning_batch_explosion_node_tree').id, 'tree'),
                (self.env.ref('x_fulfillment_planner.view_planning_batch_explosion_node_form').id, 'form'),
            ],
            'target': 'current',
            # Start from level 0 only; users can drill down into children from node form.
            'domain': [('batch_id', '=', self.id), ('parent_id', '=', False)],
            'context': {'default_batch_id': self.id, 'search_default_batch_id': self.id},
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

    @api.depends('demand_summary_ids.uncovered_qty', 'demand_summary_ids.total_demand_qty')
    def _compute_coverage_metrics(self):
        for batch in self:
            demand_total = sum(batch.demand_summary_ids.mapped('total_demand_qty'))
            shortage_total = sum(batch.demand_summary_ids.mapped('uncovered_qty'))
            batch.uncovered_demand_qty = shortage_total
            if demand_total:
                batch.mo_coverage_pct = (max(demand_total - shortage_total, 0.0) / demand_total) * 100.0
            else:
                batch.mo_coverage_pct = 0.0

    @api.depends('explosion_node_ids.item_type', 'explosion_node_ids.state')
    def _compute_explosion_metrics(self):
        for batch in self:
            nodes = batch.explosion_node_ids
            batch.semi_product_count = len(nodes.filtered(lambda n: n.item_type == 'semi').mapped('product_id'))
            batch.raw_product_count = len(nodes.filtered(lambda n: n.item_type == 'raw').mapped('product_id'))
            batch.explosion_issue_count = len(nodes.filtered(lambda n: n.state in ('cycle', 'missing_bom', 'excluded')))

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

    def _clear_explosion_data(self):
        self.explosion_node_ids.unlink()
        self.demand_summary_ids.unlink()
        self.explosion_last_run = False
        self.explosion_last_run_by = False

    def _reset_to_draft(self):
        self._clear_shortage_data()
        self._clear_explosion_data()
        self.status = 'draft'

    def _reset_shortage_on_sales_change(self):
        for batch in self:
            batch._clear_shortage_data()
            batch._clear_explosion_data()
            if batch.status in ('shortage_analyzed', 'calculated'):
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

    def _get_bom_map(self, products):
        if not products:
            return {}
        bom_map = self.env['mrp.bom']._bom_find(
            products,
            company_id=self.company_id.id,
        )
        return bom_map

    def _build_explosion(self, max_depth=5):
        self.ensure_one()
        selected_lines = self.line_ids.filtered('selected')
        if not selected_lines:
            raise UserError(_('Please select at least one Sales Order Line.'))

        self._clear_explosion_data()

        bom_cache = {}
        demand_by_product = defaultdict(lambda: {'manufacture': 0.0, 'procure': 0.0, 'levels': []})
        source_line_ids_by_product = defaultdict(set)

        def get_bom(product):
            if product.id not in bom_cache:
                bom_map = self._get_bom_map(product)
                bom_cache[product.id] = next(iter(bom_map.values()), False)
            return bom_cache[product.id]

        def add_demand(product_id, supply_type, qty, level, source_sale_line_id):
            demand_by_product[product_id][supply_type] += qty
            demand_by_product[product_id]['levels'].append(level)
            if source_sale_line_id:
                source_line_ids_by_product[product_id].add(source_sale_line_id)

        def create_node(parent_id, parent_product_id, product, qty, level, path_ids, path_key, source_sale_line_id):
            if level > max_depth:
                self.env['planning.batch.explosion.node'].create({
                    'batch_id': self.id,
                    'parent_id': parent_id,
                    'source_sale_line_id': source_sale_line_id,
                    'parent_product_id': parent_product_id,
                    'product_id': product.id,
                    'uom_id': product.uom_id.id,
                    'level': level,
                    'demand_qty': qty,
                    'item_type': 'raw' if level > 0 else 'finished',
                    'supply_type': 'procure',
                    'is_leaf': True,
                    'path_key': path_key,
                    'state': 'excluded',
                    'message': _('Excluded due to max explosion depth'),
                })
                add_demand(product.id, 'procure', qty, level, source_sale_line_id)
                return

            bom = get_bom(product)
            item_type = 'finished' if level == 0 else 'semi'
            supply_type = 'manufacture' if bom else 'procure'
            is_leaf = not bool(bom)

            node = self.env['planning.batch.explosion.node'].create({
                'batch_id': self.id,
                'parent_id': parent_id,
                'source_sale_line_id': source_sale_line_id,
                'parent_product_id': parent_product_id,
                'product_id': product.id,
                'uom_id': product.uom_id.id,
                'level': level,
                'demand_qty': qty,
                'item_type': 'raw' if not bom and level > 0 else item_type,
                'supply_type': supply_type,
                'bom_id': bom.id if bom else False,
                'is_leaf': is_leaf,
                'path_key': path_key,
                'state': 'ok',
                'message': False,
            })
            add_demand(product.id, supply_type, qty, level, source_sale_line_id)

            if not bom:
                return

            base_qty = bom.product_uom_id._compute_quantity(
                bom.product_qty or 1.0,
                product.uom_id,
            ) or 1.0
            for bom_line in bom.bom_line_ids:
                component = bom_line.product_id
                if not component:
                    continue
                comp_qty = bom_line.product_uom_id._compute_quantity(
                    bom_line.product_qty,
                    component.uom_id,
                )
                required_qty = qty * (comp_qty / base_qty)
                next_path_ids = list(path_ids)
                next_path_key = f"{path_key} > {component.display_name}"
                if component.id in next_path_ids:
                    self.env['planning.batch.explosion.node'].create({
                        'batch_id': self.id,
                        'parent_id': node.id,
                        'source_sale_line_id': source_sale_line_id,
                        'parent_product_id': product.id,
                        'product_id': component.id,
                        'uom_id': component.uom_id.id,
                        'level': level + 1,
                        'demand_qty': required_qty,
                        'item_type': 'raw',
                        'supply_type': 'procure',
                        'is_leaf': True,
                        'path_key': next_path_key,
                        'state': 'cycle',
                        'message': _('Cycle detected'),
                    })
                    add_demand(component.id, 'procure', required_qty, level + 1, source_sale_line_id)
                    continue

                next_path_ids.append(component.id)
                create_node(
                    node.id,
                    product.id,
                    component,
                    required_qty,
                    level + 1,
                    next_path_ids,
                    next_path_key,
                    source_sale_line_id,
                )

        for batch_line in selected_lines:
            product = batch_line.product_id
            if not product:
                continue
            create_node(
                parent_id=False,
                parent_product_id=False,
                product=product,
                qty=batch_line.qty_product_uom,
                level=0,
                path_ids=[product.id],
                path_key=product.display_name,
                source_sale_line_id=batch_line.sale_order_line_id.id,
            )

        products = self.env['product.product'].browse(list(demand_by_product.keys()))
        for product in products:
            values = demand_by_product[product.id]
            total_qty = values['manufacture'] + values['procure']
            available = product.with_company(self.company_id).qty_available
            uncovered = max(total_qty - available, 0.0)
            self.env['planning.batch.demand.summary'].create({
                'batch_id': self.id,
                'product_id': product.id,
                'uom_id': product.uom_id.id,
                'manufacture_demand_qty': values['manufacture'],
                'procurement_demand_qty': values['procure'],
                'total_demand_qty': total_qty,
                'available_qty': available,
                'uncovered_qty': uncovered,
                'level_min': min(values['levels']) if values['levels'] else 0,
                'level_max': max(values['levels']) if values['levels'] else 0,
                'has_bom': bool(get_bom(product)),
            })

        self.explosion_last_run = fields.Datetime.now()
        self.explosion_last_run_by = self.env.user
        return source_line_ids_by_product

    def action_analyze_structure(self):
        self.ensure_one()
        if self.status not in ['draft', 'shortage_analyzed']:
            raise UserError(_('Structure analysis can only run in Draft or Shortage Analyzed status.'))
        self._build_explosion()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Structure analysis completed'),
                'message': _('Manufacturing chain and demand summary updated.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }

    def action_analyze_shortage(self):
        self.ensure_one()
        if self.status not in ['draft', 'shortage_analyzed']:
            raise UserError(_('Shortage analysis can only be run in Draft or Shortage Analyzed status.'))

        source_line_ids_by_product = self._build_explosion()
        if not self.demand_summary_ids:
            raise UserError(_('No demand summary data found. Run structure analysis first.'))

        self.shortage_line_ids.unlink()

        mo_qty_by_product = defaultdict(float)
        mo_domain = [
            ('product_id', 'in', self.demand_summary_ids.mapped('product_id').ids),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['confirmed', 'progress']),
        ]
        for mo in self.env['mrp.production'].search(mo_domain):
            qty = mo.product_uom_id._compute_quantity(mo.product_qty, mo.product_id.uom_id)
            mo_qty_by_product[mo.product_id.id] += qty

        for line in self.demand_summary_ids:
            product = line.product_id
            source_ids = list(source_line_ids_by_product.get(product.id, set()))

            if line.manufacture_demand_qty > 0:
                on_hand = product.with_company(self.company_id).qty_available
                available_qty = on_hand + mo_qty_by_product.get(product.id, 0.0)
                shortage_qty = max(line.manufacture_demand_qty - available_qty, 0.0)
                self.env['planning.batch.shortage'].create({
                    'batch_id': self.id,
                    'product_id': product.id,
                    'uom_id': product.uom_id.id,
                    'demand_qty': line.manufacture_demand_qty,
                    'available_qty': available_qty,
                    'shortage_qty': shortage_qty,
                    'source_type': 'mo',
                    'related_line_ids': [(6, 0, source_ids)],
                })

            if line.procurement_demand_qty > 0:
                on_hand = product.with_company(self.company_id).qty_available
                available_qty = on_hand
                shortage_qty = max(line.procurement_demand_qty - available_qty, 0.0)
                self.env['planning.batch.shortage'].create({
                    'batch_id': self.id,
                    'product_id': product.id,
                    'uom_id': product.uom_id.id,
                    'demand_qty': line.procurement_demand_qty,
                    'available_qty': available_qty,
                    'shortage_qty': shortage_qty,
                    'source_type': 'po',
                    'related_line_ids': [(6, 0, source_ids)],
                })

        self.shortage_last_run = fields.Datetime.now()
        self.shortage_last_run_by = self.env.user
        self.status = 'shortage_analyzed'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shortage analysis completed'),
                'message': _('Shortage table updated from multi-level demand.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }

    def action_create_suggested_mo(self):
        self.ensure_one()
        if self.status != 'shortage_analyzed':
            raise UserError(_('Create MOs is only available after Shortage Analysis.'))
        shortage_lines = self.shortage_line_ids.filtered(lambda l: l.source_type == 'mo' and l.shortage_qty > 0)
        if not shortage_lines:
            raise UserError(_('No manufacturing shortages to create Manufacturing Orders.'))

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
                'origin': f"FP:{self.name}",
            }
            created_mos |= self.env['mrp.production'].create(mo_vals)

        if not created_mos:
            raise UserError(_('No Manufacturing Orders were created.'))

        self.mrp_production_ids = [(4, mo.id) for mo in created_mos]
        self.suggested_mo_created_at = fields.Datetime.now()
        self.suggested_mo_created_by = self.env.user
        self.status = 'calculated'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('MOs created'),
                'message': _('Manufacturing Orders created for calculated shortages.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }

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
        self._reset_to_draft()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('MOs removed'),
                'message': _('Draft Manufacturing Orders created by this batch were removed.'),
                'type': 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }
