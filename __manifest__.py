{
    'name': 'Fulfillment Planner',
    'version': '17.0.0.1.0',
    'summary': 'Fulfillment planning control module',
    'depends': ['base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/planning_batch_views.xml',
    ],
    'installable': True,
    'application': False,
}
