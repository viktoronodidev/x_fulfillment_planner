{
    'name': 'Fulfillment Planner (v0.4.26)',
    'version': '17.0.0.4.26',
    'license': 'LGPL-3',
    'summary': 'Fulfillment planning control module',
    'depends': ['base', 'sale', 'purchase', 'mrp', 'stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/planning_batch_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'x_fulfillment_planner/static/src/css/planning_batch_select_so.css',
            'x_fulfillment_planner/static/src/css/fp_ui_revamp.css',
        ],
    },
    'installable': True,
    'application': False,
}
