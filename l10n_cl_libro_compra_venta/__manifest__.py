# -*- coding: utf-8 -*-
{
   'active': False,
    'author': u'Daniel Santibañez Polanco, Blanco Martín & Asociados',
    'website': 'http://globalresponse.cl',
    'category': 'Localization/Chile',
    'demo_xml': [],
    'depends': [
        'account',
        'account_accountant',
        'l10n_cl_invoice',
        'l10n_cl_base_rut',
        'l10n_cl_partner_activities',
        'report_xlsx'
        ],
    'description': u'''
Chile - Libros mensuales de Compra y Venta
''',
    #  'init_xml': [
    #     'line_tax_view.sql'
    # ],
    'installable': True,
    'license': 'AGPL-3',
    'name': u'Chile - Libros mensuales de Compra y Venta',
    'test': [],
    'data': [
        'views/libro_compra_venta.xml',
        'views/libro_honorarios.xml',
        'views/consumo_folios.xml',
        'views/export.xml',
        'wizard/build_and_send_moves.xml',
        #'security/ir.model.access.csv',
        ],
    'version': '10.0.3.1.0',
}
