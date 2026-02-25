from odoo import api, fields, models


class ProcurementBatchVendorConfirmWizardLine(models.TransientModel):
    _name = 'procurement.batch.vendor.confirm.wizard.line'
    _description = 'Procurement Vendor Confirmation Wizard Line'

    wizard_id = fields.Many2one(
        comodel_name='procurement.batch.vendor.confirm.wizard',
        required=True,
        ondelete='cascade',
    )
    batch_line_id = fields.Many2one(
        comodel_name='procurement.batch.line',
        string='Analysis Line',
        required=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        related='batch_line_id.product_id',
        string='Product',
        readonly=True,
    )
    suggested_qty = fields.Float(
        related='batch_line_id.suggested_qty',
        string='Suggested Qty',
        readonly=True,
    )
    uom_id = fields.Many2one(
        related='batch_line_id.uom_id',
        string='UoM',
        readonly=True,
    )
    supplierinfo_ids = fields.Many2many(
        comodel_name='product.supplierinfo',
        compute='_compute_supplierinfo_ids',
        string='Supplier Infos',
        readonly=True,
    )
    vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Preferred Vendor',
        required=True,
        domain="[('id', 'in', supplier_partner_ids)]",
    )
    supplier_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        compute='_compute_supplierinfo_ids',
        string='Available Vendors',
        readonly=True,
    )
    selected_price = fields.Float(string='Selected Price', compute='_compute_selected_metrics', readonly=True)
    selected_delay = fields.Float(string='Selected Lead Time (days)', compute='_compute_selected_metrics', readonly=True)
    best_price = fields.Float(string='Best Price', compute='_compute_market_metrics', readonly=True)
    fastest_delay = fields.Float(string='Fastest Lead Time (days)', compute='_compute_market_metrics', readonly=True)
    confirmed = fields.Boolean(string='Confirmed', default=False)

    @api.depends('batch_line_id', 'batch_line_id.product_id', 'wizard_id.batch_id.company_id')
    def _compute_supplierinfo_ids(self):
        for line in self:
            company = line.wizard_id.batch_id.company_id
            sellers = line.batch_line_id.product_id.seller_ids.filtered(
                lambda s: not s.company_id or s.company_id == company
            )
            line.supplierinfo_ids = sellers
            line.supplier_partner_ids = sellers.mapped('partner_id')

    @api.depends('vendor_id', 'supplierinfo_ids')
    def _compute_selected_metrics(self):
        for line in self:
            seller = line.supplierinfo_ids.filtered(lambda s: s.partner_id == line.vendor_id)[:1]
            line.selected_price = seller.price if seller else 0.0
            line.selected_delay = seller.delay if seller else 0.0

    @api.depends('supplierinfo_ids')
    def _compute_market_metrics(self):
        for line in self:
            prices = line.supplierinfo_ids.mapped('price')
            delays = line.supplierinfo_ids.mapped('delay')
            line.best_price = min(prices) if prices else 0.0
            line.fastest_delay = min(delays) if delays else 0.0
