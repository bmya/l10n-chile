# -*- coding: utf-8 -*-
{
    'author': u'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'category': 'Localization/Chile',
    'demo_xml': [],
    'depends': [
        'account',
        'account_accountant',
        'l10n_cl_invoice',
        'l10n_cl_base_rut',
        'l10n_cl_partner_activities',
        ],
    'license': 'LGPL-3',
    'name': u'Chile - Información de purchase/sale',
    'test': [],
    'data': [
        # 'views/export_invoice_report.xml',
        # 'views/fee_report.xml',
        # 'views/receipt_consumption_report.xml',
        'views/sale_purchase_report.xml',
        'wizard/account_move_send_multi.xml',
        ],
    'version': '10.0.1.0.0',
    'active': False,
    'installable': True,
}
