from odoo import fields, models


class ProcurementBatchLine(models.Model):
    _name = 'procurement.batch.line'
    _description = 'Procurement Batch Analysis Line'
    _order = 'suggested_qty desc, product_id'

    batch_id = fields.Many2one(
        comodel_name='procurement.batch',
        string='Procurement Batch',
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
    min_stock_target_qty = fields.Float(string='Min Stock Target Qty')
    total_target_qty = fields.Float(string='Total Target Qty')
    available_qty = fields.Float(string='Available Qty')
    uncovered_qty = fields.Float(string='Uncovered Qty')
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
