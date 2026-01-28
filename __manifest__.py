{
    'name': 'Fulfillment Planner (v0.3.03)',
    'version': '17.0.0.3.03',
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
        ],
    },
    'installable': True,
    'application': False,
}
