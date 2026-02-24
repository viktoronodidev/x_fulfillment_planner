from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    schedule_date = fields.Date(
        string='Schedule Date',
    )
    priority = fields.Selection(
        [
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
        ],
        string='Priority',
        default='3',
    )
    fulfillment_batch_ids = fields.Many2many(
        comodel_name='planning.batch',
        relation='planning_batch_sale_order_rel',
        column1='sale_order_id',
        column2='planning_batch_id',
        string='Fulfillment Batches',
        readonly=True,
    )
    fulfillment_batch_count = fields.Integer(
        string='Fulfillment Batches',
        compute='_compute_fulfillment_batch_count',
    )
    fulfillment_locked = fields.Boolean(
        string='Fulfillment Locked',
        compute='_compute_fulfillment_locked',
    )
    fulfillment_state = fields.Selection(
        [
            ('new', 'New'),
            ('planned', 'Planned'),
            ('delivered', 'Delivered'),
            ('invoiced', 'Invoiced'),
        ],
        string='Fulfillment Status',
        compute='_compute_fulfillment_state',
        store=True,
    )

    @api.depends('fulfillment_batch_ids')
    def _compute_fulfillment_batch_count(self):
        for order in self:
            order.fulfillment_batch_count = len(order.fulfillment_batch_ids)

    @api.depends('order_line.planning_batch_line_ids')
    def _compute_fulfillment_locked(self):
        line_data = self.env['planning.batch.line'].read_group(
            [('sale_order_id', 'in', self.ids)],
            ['sale_order_id'],
            ['sale_order_id'],
        )
        locked_map = {data['sale_order_id'][0]: data['sale_order_id_count'] for data in line_data}
        for order in self:
            order.fulfillment_locked = bool(locked_map.get(order.id))

    @api.depends('order_line.fulfillment_state', 'order_line.display_type')
    def _compute_fulfillment_state(self):
        for order in self:
            lines = order.order_line.filtered(lambda l: not l.display_type)
            if not lines:
                order.fulfillment_state = 'new'
                continue
            states = set(lines.mapped('fulfillment_state'))
            if states == {'invoiced'}:
                order.fulfillment_state = 'invoiced'
            elif states == {'delivered'}:
                order.fulfillment_state = 'delivered'
            elif states == {'planned'}:
                order.fulfillment_state = 'planned'
            else:
                order.fulfillment_state = 'new'

    def action_view_fulfillment_batches(self):
        self.ensure_one()
        action = self.env.ref('x_fulfillment_planner.action_planning_batch').read()[0]
        action['domain'] = [('id', 'in', self.fulfillment_batch_ids.ids)]
        action['context'] = dict(self.env.context)
        return action

    def write(self, vals):
        if 'order_line' in vals:
            locked = self.filtered('fulfillment_locked')
            if locked:
                raise UserError(_(
                    'Sales order is already in planning batch - you cannot modify line items until it is removed.'
                ))
        return super().write(vals)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    reserved = fields.Boolean(
        string='Reserved',
        default=False,
    )
    planning_batch_line_ids = fields.One2many(
        comodel_name='planning.batch.line',
        inverse_name='sale_order_line_id',
        string='Planning Batch Lines',
        readonly=True,
    )
    fulfillment_state = fields.Selection(
        [
            ('new', 'New'),
            ('planned', 'Planned'),
            ('delivered', 'Delivered'),
            ('invoiced', 'Invoiced'),
        ],
        string='Fulfillment Status',
        compute='_compute_fulfillment_state',
        store=True,
    )

    @api.depends('qty_delivered', 'product_uom_qty', 'invoice_status', 'planning_batch_line_ids')
    def _compute_fulfillment_state(self):
        in_batch = {line.id for line in self if line.planning_batch_line_ids}
        for line in self:
            if line.display_type:
                line.fulfillment_state = 'new'
                continue
            if line.invoice_status == 'invoiced':
                line.fulfillment_state = 'invoiced'
            elif line.product_uom_qty and line.qty_delivered >= line.product_uom_qty:
                line.fulfillment_state = 'delivered'
            elif line.id in in_batch:
                line.fulfillment_state = 'planned'
            else:
                line.fulfillment_state = 'new'

    def _reset_linked_batches(self):
        batch_lines = self.env['planning.batch.line'].search([
            ('sale_order_line_id', 'in', self.ids),
        ])
        batches = batch_lines.mapped('batch_id')
        batches._reset_shortage_on_sales_change()

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        orders = self.env['sale.order']
        for vals in vals_list:
            if vals.get('order_id'):
                orders |= self.env['sale.order'].browse(vals['order_id'])
        locked = orders.filtered('fulfillment_locked')
        if locked:
            raise UserError(_(
                'Sales order is already in planning batch - you cannot modify line items until it is removed.'
            ))
        return super().create(vals_list)

    def write(self, vals):
        allowed_fields = {'price_unit', 'discount', 'tax_id', 'reserved'}
        if vals:
            if any(field not in allowed_fields for field in vals.keys()):
                locked = self.mapped('order_id').filtered('fulfillment_locked')
                if locked:
                    raise UserError(_(
                        'Sales order is already in planning batch - you cannot modify line items until it is removed.'
                    ))
        res = super().write(vals)
        if vals:
            self._reset_linked_batches()
        return res

    def unlink(self):
        locked = self.mapped('order_id').filtered('fulfillment_locked')
        if locked:
            raise UserError(_(
                'Sales order is already in planning batch - you cannot modify line items until it is removed.'
            ))
        batch_lines = self.env['planning.batch.line'].search([
            ('sale_order_line_id', 'in', self.ids),
        ])
        batches = batch_lines.mapped('batch_id')
        res = super().unlink()
        batches._reset_shortage_on_sales_change()
        return res
