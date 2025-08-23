{
    'name': 'Department Recruitment Analysis',
    'version': '17.0.1.0.0',
    'summary': 'Predict and analyze recruitment needs by department',
    'category': 'Human Resources',
    'depends': ['hr', 'hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_recruit_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
