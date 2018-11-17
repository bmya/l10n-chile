# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016 Blanco Martín & Asociados - Odoo Chile Community
#
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
    "name": "Chile Localization. Get a Clean Translation",
    "version": "10.0.1.0",
    "description": """
This addon, clears all chilean translations, so that
you can get a new one using this odoo start switch:
"--stop-after-init --load-language=es_CL"
    """,
    "author": "Blanco Martín & Asociados",
    "website": "http://blancomartin.cl",
    "category": "Localization/Language",
    'init_xml': [
        'query.sql'
        ],
    "active": False,
    "installable": True}
