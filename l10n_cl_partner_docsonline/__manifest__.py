# -*- coding: utf-8 -*-
##############################################################################
##
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Webservice que consulta contribuyentes en Documentos Online',
    'version': '10.0.1.0.0',
    'category': 'BMYA Enhancements/Localization',
    'description': """
Webservice rut -> giros, dte de intercambio
===========================================
Allows to ask for tax payers data
    """,
    'author':  u'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'depends': [
        'base',
        'website',
        'l10n_cl_invoice',
        'l10n_cl_dte',
    ],
    'data': [
        'data/ir.config_parameter.xml',
        'views/partner_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
