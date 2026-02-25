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
            ('shortage_analyzed', 'Analyzed'),
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
    procurement_line_ids = fields.One2many(
        comodel_name='planning.batch.procurement.line',
        inverse_name='batch_id',
        string='Procurement Lines',
        readonly=True,
    )
    shortage_line_ids = fields.One2many(
        comodel_name='planning.batch.shortage',
        inverse_name='batch_id',
        string='Shortage Lines',
        readonly=True,
    )
    shortage_level0_ids = fields.One2many(
        comodel_name='planning.batch.shortage',
        compute='_compute_shortage_level_ids',
        string='Shortage Level 0',
    )
    shortage_level1_ids = fields.One2many(
        comodel_name='planning.batch.shortage',
        compute='_compute_shortage_level_ids',
        string='Shortage Level 1',
    )
    shortage_level2_ids = fields.One2many(
        comodel_name='planning.batch.shortage',
        compute='_compute_shortage_level_ids',
        string='Shortage Level 2',
    )
    shortage_level3_ids = fields.One2many(
        comodel_name='planning.batch.shortage',
        compute='_compute_shortage_level_ids',
        string='Shortage Level 3',
    )
    shortage_level4_ids = fields.One2many(
        comodel_name='planning.batch.shortage',
        compute='_compute_shortage_level_ids',
        string='Shortage Level 4',
    )
    has_shortage_level0 = fields.Boolean(compute='_compute_shortage_level_flags')
    has_shortage_level1 = fields.Boolean(compute='_compute_shortage_level_flags')
    has_shortage_level2 = fields.Boolean(compute='_compute_shortage_level_flags')
    has_shortage_level3 = fields.Boolean(compute='_compute_shortage_level_flags')
    has_shortage_level4 = fields.Boolean(compute='_compute_shortage_level_flags')
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
    chain_line_ids = fields.One2many(
        comodel_name='planning.batch.chain.line',
        inverse_name='batch_id',
        string='Manufacturing Chain Lines',
        readonly=True,
    )
    explosion_root_node_ids = fields.One2many(
        comodel_name='planning.batch.explosion.node',
        inverse_name='batch_id',
        string='Root Explosion Nodes',
        compute='_compute_explosion_root_node_ids',
    )
    explosion_level0_ids = fields.One2many(
        comodel_name='planning.batch.explosion.node',
        compute='_compute_explosion_level_ids',
        string='Explosion Level 0',
    )
    explosion_level1_ids = fields.One2many(
        comodel_name='planning.batch.explosion.node',
        compute='_compute_explosion_level_ids',
        string='Explosion Level 1',
    )
    explosion_level2_ids = fields.One2many(
        comodel_name='planning.batch.explosion.node',
        compute='_compute_explosion_level_ids',
        string='Explosion Level 2',
    )
    explosion_level3_ids = fields.One2many(
        comodel_name='planning.batch.explosion.node',
        compute='_compute_explosion_level_ids',
        string='Explosion Level 3',
    )
    explosion_level4_ids = fields.One2many(
        comodel_name='planning.batch.explosion.node',
        compute='_compute_explosion_level_ids',
        string='Explosion Level 4',
    )
    has_explosion_level0 = fields.Boolean(compute='_compute_explosion_level_flags')
    has_explosion_level1 = fields.Boolean(compute='_compute_explosion_level_flags')
    has_explosion_level2 = fields.Boolean(compute='_compute_explosion_level_flags')
    has_explosion_level3 = fields.Boolean(compute='_compute_explosion_level_flags')
    has_explosion_level4 = fields.Boolean(compute='_compute_explosion_level_flags')
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
    procurement_last_run = fields.Datetime(
        string='Procurement Analyzed At',
        readonly=True,
    )
    procurement_last_run_by = fields.Many2one(
        comodel_name='res.users',
        string='Procurement Analyzed By',
        readonly=True,
    )
    procurement_include_open_demands = fields.Boolean(
        string='Scope: Open Demands',
        readonly=True,
    )
    procurement_include_min_stock = fields.Boolean(
        string='Scope: Minimum Stock',
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
            'res_model': 'planning.batch.chain.line',
            'view_mode': 'tree',
            'views': [
                (self.env.ref('x_fulfillment_planner.view_planning_batch_chain_line_tree').id, 'tree'),
            ],
            'target': 'current',
            'domain': [('batch_id', '=', self.id)],
            'context': {
                'default_batch_id': self.id,
                'search_default_batch_id': self.id,
            },
        }

    def action_open_procurement_scope(self):
        self.ensure_one()
        wizard = self.env['planning.batch.procurement.scope.wizard'].create({
            'batch_id': self.id,
            'include_open_demands': True,
            'include_min_stock': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Analyze Procurement'),
            'res_model': 'planning.batch.procurement.scope.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wizard.id,
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

    @api.depends('explosion_node_ids.parent_id')
    def _compute_explosion_root_node_ids(self):
        for batch in self:
            batch.explosion_root_node_ids = batch.explosion_node_ids.filtered(lambda n: not n.parent_id)

    @api.depends('explosion_node_ids.level')
    def _compute_explosion_level_ids(self):
        for batch in self:
            batch.explosion_level0_ids = batch.explosion_node_ids.filtered(lambda n: n.level == 0)
            batch.explosion_level1_ids = batch.explosion_node_ids.filtered(lambda n: n.level == 1)
            batch.explosion_level2_ids = batch.explosion_node_ids.filtered(lambda n: n.level == 2)
            batch.explosion_level3_ids = batch.explosion_node_ids.filtered(lambda n: n.level == 3)
            batch.explosion_level4_ids = batch.explosion_node_ids.filtered(lambda n: n.level == 4)

    @api.depends('explosion_level0_ids', 'explosion_level1_ids', 'explosion_level2_ids', 'explosion_level3_ids', 'explosion_level4_ids')
    def _compute_explosion_level_flags(self):
        for batch in self:
            batch.has_explosion_level0 = bool(batch.explosion_level0_ids)
            batch.has_explosion_level1 = bool(batch.explosion_level1_ids)
            batch.has_explosion_level2 = bool(batch.explosion_level2_ids)
            batch.has_explosion_level3 = bool(batch.explosion_level3_ids)
            batch.has_explosion_level4 = bool(batch.explosion_level4_ids)

    @api.depends('shortage_line_ids.level')
    def _compute_shortage_level_ids(self):
        for batch in self:
            batch.shortage_level0_ids = batch.shortage_line_ids.filtered(lambda l: l.level == 0)
            batch.shortage_level1_ids = batch.shortage_line_ids.filtered(lambda l: l.level == 1)
            batch.shortage_level2_ids = batch.shortage_line_ids.filtered(lambda l: l.level == 2)
            batch.shortage_level3_ids = batch.shortage_line_ids.filtered(lambda l: l.level == 3)
            batch.shortage_level4_ids = batch.shortage_line_ids.filtered(lambda l: l.level == 4)

    @api.depends('shortage_level0_ids', 'shortage_level1_ids', 'shortage_level2_ids', 'shortage_level3_ids', 'shortage_level4_ids')
    def _compute_shortage_level_flags(self):
        for batch in self:
            batch.has_shortage_level0 = bool(batch.shortage_level0_ids)
            batch.has_shortage_level1 = bool(batch.shortage_level1_ids)
            batch.has_shortage_level2 = bool(batch.shortage_level2_ids)
            batch.has_shortage_level3 = bool(batch.shortage_level3_ids)
            batch.has_shortage_level4 = bool(batch.shortage_level4_ids)

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
        self.chain_line_ids.unlink()
        self.demand_summary_ids.unlink()
        self.explosion_last_run = False
        self.explosion_last_run_by = False

    def _clear_procurement_data(self):
        self.procurement_line_ids.unlink()
        self.procurement_last_run = False
        self.procurement_last_run_by = False
        self.procurement_include_open_demands = False
        self.procurement_include_min_stock = False

    def _reset_to_draft(self):
        self._clear_shortage_data()
        self._clear_explosion_data()
        self._clear_procurement_data()
        self.status = 'draft'

    def _reset_shortage_on_sales_change(self):
        for batch in self:
            batch._clear_shortage_data()
            batch._clear_explosion_data()
            batch._clear_procurement_data()
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
        chain_aggregate = defaultdict(
            lambda: {
                'demand_qty': 0.0,
                'state': 'ok',
                'message': False,
            }
        )
        state_priority = {
            'ok': 0,
            'excluded': 1,
            'missing_bom': 2,
            'cycle': 3,
        }

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

        def add_chain_line(root_product, product, qty, level, item_type, supply_type, state, message):
            key = (
                root_product.id,
                level,
                product.id,
                product.uom_id.id,
                item_type,
                supply_type,
            )
            line = chain_aggregate[key]
            line['demand_qty'] += qty
            if state_priority.get(state, 0) >= state_priority.get(line['state'], 0):
                line['state'] = state
                line['message'] = message or line['message']

        def create_node(root_product, parent_id, parent_product_id, product, qty, level, path_ids, path_key, source_sale_line_id):
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
                add_chain_line(
                    root_product=root_product,
                    product=product,
                    qty=qty,
                    level=level,
                    item_type='raw' if level > 0 else 'finished',
                    supply_type='procure',
                    state='excluded',
                    message=_('Excluded due to max explosion depth'),
                )
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
            add_chain_line(
                root_product=root_product,
                product=product,
                qty=qty,
                level=level,
                item_type='raw' if not bom and level > 0 else item_type,
                supply_type=supply_type,
                state='ok',
                message=False,
            )

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
                    add_chain_line(
                        root_product=root_product,
                        product=component,
                        qty=required_qty,
                        level=level + 1,
                        item_type='raw',
                        supply_type='procure',
                        state='cycle',
                        message=_('Cycle detected'),
                    )
                    add_demand(component.id, 'procure', required_qty, level + 1, source_sale_line_id)
                    continue

                next_path_ids.append(component.id)
                create_node(
                    root_product,
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
                root_product=product,
                parent_id=False,
                parent_product_id=False,
                product=product,
                qty=batch_line.qty_product_uom,
                level=0,
                path_ids=[product.id],
                path_key=product.display_name,
                source_sale_line_id=batch_line.sale_order_line_id.id,
            )

        chain_values = [(5, 0, 0)]
        for key, values in sorted(chain_aggregate.items(), key=lambda item: item[0]):
            root_id, level, product_id, uom_id, item_type, supply_type = key
            chain_values.append((0, 0, {
                'root_product_id': root_id,
                'level': level,
                'product_id': product_id,
                'demand_qty': values['demand_qty'],
                'uom_id': uom_id,
                'item_type': item_type,
                'supply_type': supply_type,
                'state': values['state'],
                'message': values['message'],
            }))
        self.chain_line_ids = chain_values

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

    def action_analyze(self):
        self.ensure_one()
        return self.action_analyze_shortage()

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
                    'level': line.level_min or 0,
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
                    'level': line.level_min or 0,
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
                'message': _('Analysis completed. Structure and shortage data are updated.'),
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

    def action_revert_to_draft(self):
        self.ensure_one()
        if self.status != 'calculated':
            raise UserError(_('Revert to Draft is only available in Calculated status.'))
        return self.action_undo_created_mo()

    def action_confirm_all_mos(self):
        self.ensure_one()
        if self.status != 'calculated':
            raise UserError(_('Confirm all MOs is only available in Calculated status.'))

        if not self.mrp_production_ids:
            raise UserError(_('There are no Manufacturing Orders in this batch.'))

        draft_mos = self.mrp_production_ids.filtered(lambda mo: mo.state == 'draft')
        if draft_mos:
            draft_mos.action_confirm()

        self.status = 'confirmed'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Manufacturing Orders confirmed'),
                'message': _('All draft Manufacturing Orders in this batch were confirmed.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }

    def _try_mark_done(self):
        self.ensure_one()
        if self.status != 'confirmed' or not self.mrp_production_ids:
            return
        open_mos = self.mrp_production_ids.filtered(lambda mo: mo.state not in ('done', 'cancel'))
        if not open_mos:
            self.status = 'done'

    def action_check_manufacturing_orders(self):
        self.ensure_one()
        self._try_mark_done()
        wizard = self.env['planning.batch.mo.check.wizard'].create({
            'batch_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Check Manufacturing Orders'),
            'res_model': 'planning.batch.mo.check.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wizard.id,
        }

    def _get_global_open_procurement_demand(self):
        """Return remaining raw material demand grouped by component product."""
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

    def action_analyze_procurement(self, include_open_demands=True, include_min_stock=True):
        self.ensure_one()
        if self.status not in ['confirmed', 'done']:
            raise UserError(_('Analyze Procurement is only available in Confirmed or Done status.'))
        if not include_open_demands and not include_min_stock:
            raise UserError(_('At least one demand source must be enabled.'))

        products = self.env['product.product']
        open_demand_by_product = defaultdict(float)
        if include_open_demands:
            open_demand_by_product = self._get_global_open_procurement_demand()
            products |= self.env['product.product'].browse(list(open_demand_by_product.keys()))

        min_by_product = defaultdict(float)
        if include_min_stock:
            orderpoint_products = self.env['stock.warehouse.orderpoint'].search([
                ('company_id', '=', self.company_id.id),
            ]).mapped('product_id')
            products |= orderpoint_products
            min_by_product = self._get_min_stock_targets(products)

        if not products:
            self._clear_procurement_data()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No procurement demand'),
                    'message': _('No products found for selected procurement scope.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        open_proc_qty = self._get_open_procurement_qty(products)
        values = [(5, 0, 0)]
        for product in products.sorted('display_name'):
            if product.type == 'service':
                continue
            open_demand = open_demand_by_product.get(product.id, 0.0) if include_open_demands else 0.0
            available = product.with_company(self.company_id).qty_available
            min_target = min_by_product.get(product.id, 0.0) if include_min_stock else 0.0
            min_demand = max(min_target - available, 0.0) if include_min_stock else 0.0
            total_demand = open_demand + min_demand
            existing_open_qty = open_proc_qty.get(product.id, 0.0)
            suggested = max(total_demand - available - existing_open_qty, 0.0)
            vendor = self._pick_vendor(product)

            status = 'no_demand'
            message = _('No action needed')
            if suggested > 0 and not vendor:
                status = 'missing_vendor'
                message = _('Missing vendor on product')
            elif suggested > 0:
                status = 'ready'
                message = False

            values.append((0, 0, {
                'product_id': product.id,
                'uom_id': product.uom_id.id,
                'vendor_id': vendor.id if vendor else False,
                'open_demand_qty': open_demand,
                'min_stock_demand_qty': min_demand,
                'total_demand_qty': total_demand,
                'available_qty': available,
                'existing_open_rfq_qty': existing_open_qty,
                'suggested_qty': suggested,
                'status': status,
                'message': message,
            }))

        self.procurement_line_ids = values
        self.procurement_last_run = fields.Datetime.now()
        self.procurement_last_run_by = self.env.user
        self.procurement_include_open_demands = include_open_demands
        self.procurement_include_min_stock = include_min_stock

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
            'origin': f"FP:{self.name}",
        })

    def action_create_procurement_rfqs(self):
        self.ensure_one()
        lines = self.procurement_line_ids.filtered(lambda l: l.suggested_qty > 0)
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
                # Re-check open procurement to avoid duplicate planning if another RFQ appeared since analysis.
                open_qty = self._get_open_procurement_qty(line.product_id).get(line.product_id.id, 0.0)
                remaining = max(line.total_demand_qty - line.available_qty - open_qty, 0.0)
                if remaining <= 0:
                    continue
                qty_po_uom = line.product_id.uom_id._compute_quantity(remaining, line.product_id.uom_po_id)
                qty_po_uom = line.product_id.uom_po_id._compute_quantity(qty_po_uom, line.product_id.uom_po_id, rounding_method='UP')
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

        self.purchase_order_ids = [(4, po.id) for po in created_pos]
        self.purchase_order_line_ids = [(4, pol.id) for pol in created_lines]
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('RFQs created'),
                'message': _('Procurement RFQs were created/updated from planner suggestions.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }
