# -*- coding: utf-8 -*-
{
    "name": """Chile - DTEs Entrantes\
    """,
    'version': '10.0.1.1.0',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'BMyA SA - Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'license': 'AGPL-3',
    'depends': [
        'sale', 'purchase',
        'mail',
        'l10n_cl_counties',
        'l10n_cl_invoice',
        'l10n_cl_dte',
        'sale_automatic_workflow',
        ],
    'external_dependencies': {
        'python': [
            'pysiidte',
            'xmltodict',
            'dicttoxml',
            'elaphe',
            'M2Crypto',
            'base64',
            'hashlib',
            'cchardet',
            'suds',
            'urllib3',
            'SOAPpy',
            'signxml',
            'ast'
        ]
    },
    'data': [
        'views/dte_incoming_views.xml',
        'views/sale_order_view.xml',
        'views/invoice_view.xml',
        'data/cron.xml',
        'data/ir.config_parameter.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
