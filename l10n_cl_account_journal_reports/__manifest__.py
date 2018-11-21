# -*- coding: utf-8 -*-
{
    'version': '10.0.1.0.0',
    'author': u'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'category': 'Localization/Chile',
    'demo_xml': [],
    'depends': [
        # 'report', para 10.0
        'account',
        'account_accountant',
    ],
    'license': 'AGPL-3',
    'name': u'Chile - Impresión de Extractos de Diario a partir de asientos o apuntes contables',
    'test': [],
    'data': [
        'views/account_journal_templates.xml',
        'report/reports.xml',
        'wizard/account_journal_wizard.xml',
    ],
    'installable': True,
    'active': False,
}
