{
    'name': 'Fulfillment Planner (v0.6.08)',
    'version': '17.0.0.6.08',
    'license': 'LGPL-3',
    'summary': 'Fulfillment planning control module',
    'depends': ['base', 'sale', 'purchase', 'mrp', 'stock', 'spreadsheet_dashboard'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/ui_defaults.xml',
        'views/planning_batch_views.xml',
        'views/sale_order_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'assets': {
        'web.assets_backend': [
            'x_fulfillment_planner/static/src/css/planning_batch_select_so.css',
            'x_fulfillment_planner/static/src/css/fp_ui_revamp.css',
        ],
    },
    'installable': True,
    'application': False,
}
