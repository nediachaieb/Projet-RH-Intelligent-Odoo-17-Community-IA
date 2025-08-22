{
    "name": "Employee AI Matching",
    "version": "17.0.1.0.0",  # ✅ format valide selon Odoo 17
    "category": "Human Resources",
    "summary": "Matching IA entre CV et description de poste",
    "license": "LGPL-3",
    "depends": ["hr"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_job_matching_inherit.xml"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
