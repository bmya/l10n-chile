# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (c) 2018 Konos Soluciones y Servicios Limitada http://www.konos.cl
{
    'name': 'Chilean Eight Columns Balance',
    'category': 'Localization',
    'version': '10.0.1.0.1',
    'author': 'Konos, Blanco Martín & Asociados',
    'website': 'http://konos.cl',
    'data': [
         'views/account_report_trial_balance_xlsx.xml',
         'views/layout.xml',
         'report/eight_columns_balance_xls_report.xml',
         'views/menuitem.xml',
    ],
    'depends': [
        'account',
        'l10n_cl_invoice',
        'report_xlsx',
    ],
    'installable': True,
}
