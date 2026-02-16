from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref('x_fulfillment_planner.action_planning_batch', raise_if_not_found=False)
    if not action:
        return

    users = env['res.users'].search([
        ('share', '=', False),
        ('active', '=', True),
    ])
    users.write({'action_id': action.id})
