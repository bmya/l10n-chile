# -*- coding: utf-8 -*-
{
    "name": """Chile - DTEs Entrantes\
    """,
    'version': '10.0.1.0.0',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'BMyA SA - Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Chile: Module to mantain incoming DTEs
""",
    'depends': [
        'mail',
        'l10n_cl_counties',
        'l10n_cl_invoice',
        'l10n_cl_dte',
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
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
