from odoo import _, fields, models
from odoo.exceptions import UserError


class PlanningBatchProcurementScopeWizard(models.TransientModel):
    _name = 'planning.batch.procurement.scope.wizard'
    _description = 'Planning Batch Procurement Scope Wizard'

    batch_id = fields.Many2one(
        comodel_name='planning.batch',
        string='Batch',
        required=True,
        readonly=True,
    )
    include_open_demands = fields.Boolean(string='Open Demands', default=True)
    include_min_stock = fields.Boolean(string='Minimum Stock Quantities', default=True)

    def action_analyze(self):
        self.ensure_one()
        if not self.include_open_demands and not self.include_min_stock:
            raise UserError(_('At least one demand source must be enabled.'))
        return self.batch_id.action_analyze_procurement(
            include_open_demands=self.include_open_demands,
            include_min_stock=self.include_min_stock,
        )
