from odoo import fields, models


class PlanningBatchProcurementLine(models.Model):
    _name = 'planning.batch.procurement.line'
    _description = 'Planning Batch Procurement Analysis Line'
    _order = 'suggested_qty desc, product_id'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='batch_id.company_id',
        string='Company',
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        index=True,
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UoM',
        required=True,
    )
    vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
    )
    open_demand_qty = fields.Float(string='Open Demand Qty')
    min_stock_demand_qty = fields.Float(string='Min Stock Demand Qty')
    total_demand_qty = fields.Float(string='Total Demand Qty')
    available_qty = fields.Float(string='Available Qty')
    existing_open_rfq_qty = fields.Float(string='Open RFQ/PO Qty')
    suggested_qty = fields.Float(string='Suggested Buy Qty')
    status = fields.Selection(
        [
            ('ready', 'Ready'),
            ('missing_vendor', 'Missing Vendor'),
            ('no_demand', 'No Demand'),
        ],
        string='Status',
        default='no_demand',
        required=True,
    )
    message = fields.Char(string='Message')
