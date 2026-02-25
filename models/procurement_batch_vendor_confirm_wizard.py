from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProcurementBatchVendorConfirmWizard(models.TransientModel):
    _name = 'procurement.batch.vendor.confirm.wizard'
    _description = 'Procurement Vendor Confirmation Wizard'

    batch_id = fields.Many2one(
        comodel_name='procurement.batch',
        string='Procurement Batch',
        required=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        comodel_name='procurement.batch.vendor.confirm.wizard.line',
        inverse_name='wizard_id',
        string='Lines to Confirm',
    )
    all_confirmed = fields.Boolean(
        string='All Confirmed',
        compute='_compute_all_confirmed',
        readonly=True,
    )

    @api.depends('line_ids.confirmed', 'line_ids.vendor_id')
    def _compute_all_confirmed(self):
        for wizard in self:
            wizard.all_confirmed = bool(
                wizard.line_ids
                and all(line.confirmed and line.vendor_id for line in wizard.line_ids)
            )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        batch = self.env['procurement.batch'].browse(self.env.context.get('default_batch_id'))
        if not batch:
            return values

        multi_vendor_lines = batch.line_ids.filtered(
            lambda l: l.suggested_qty > 0 and l.has_multi_vendor
        )
        values['line_ids'] = [(0, 0, {
            'batch_line_id': line.id,
            'vendor_id': line.vendor_id.id,
        }) for line in multi_vendor_lines]
        return values

    def action_confirm_vendors(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('There are no multi-vendor lines to confirm.'))
        invalid = self.line_ids.filtered(lambda l: not l.confirmed or not l.vendor_id)
        if invalid:
            raise UserError(_('Please confirm a vendor for each line before continuing.'))

        for line in self.line_ids:
            line.batch_line_id.vendor_id = line.vendor_id.id

        self.batch_id.status = 'vendors_confirmed'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Vendors confirmed'),
                'message': _('Vendor selection has been confirmed. You can now create RFQs.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }
