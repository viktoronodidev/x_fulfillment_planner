from odoo import fields, models


class PlanningBatchMoCheckWizard(models.TransientModel):
    _name = 'planning.batch.mo.check.wizard'
    _description = 'Planning Batch MO Check Wizard'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        readonly=True,
    )
    open_mo_ids = fields.Many2many(
        comodel_name='mrp.production',
        compute='_compute_mo_groups',
        string='Open',
        readonly=True,
    )
    closed_mo_ids = fields.Many2many(
        comodel_name='mrp.production',
        compute='_compute_mo_groups',
        string='Closed',
        readonly=True,
    )
    canceled_mo_ids = fields.Many2many(
        comodel_name='mrp.production',
        compute='_compute_mo_groups',
        string='Canceled',
        readonly=True,
    )

    @fields.depends('batch_id', 'batch_id.mrp_production_ids', 'batch_id.mrp_production_ids.state')
    def _compute_mo_groups(self):
        for wizard in self:
            mos = wizard.batch_id.mrp_production_ids
            wizard.open_mo_ids = mos.filtered(lambda m: m.state == 'confirmed')
            wizard.closed_mo_ids = mos.filtered(lambda m: m.state == 'done')
            wizard.canceled_mo_ids = mos.filtered(lambda m: m.state == 'cancel')
