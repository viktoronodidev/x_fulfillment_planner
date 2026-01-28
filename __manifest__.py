{
    'name': 'Fulfillment Planner (v0.3.01)',
    'version': '17.0.0.3.01',
    'summary': 'Fulfillment planning control module',
    'depends': ['base', 'sale', 'purchase', 'mrp', 'stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/planning_batch_views.xml',
    ],
    'installable': True,
    'application': False,
}
