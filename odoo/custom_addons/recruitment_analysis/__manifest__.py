{
    'name': 'Department Recruitment Analysis',
    'version': '17.0.1',
    'summary': 'Predict and analyze recruitment needs by department',
    'category': 'Human Resources',
    'depends': ['hr', 'hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'views/department_analysis_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
