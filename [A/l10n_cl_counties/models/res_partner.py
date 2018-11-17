# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
# Copyright (c) 2012 Cubic ERP - Teradata SAC. (http://cubicerp.com).
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _default_country(self):
        return self.env.ref('base.cl')

    city_id = fields.Many2one(
        "res.country.state.city", 'City',
        domain="[('country_id', '=', country_id)]")
    country_id = fields.Many2one(
        "res.country", 'Country',
        default=_default_country)

    @api.onchange('city_id', 'city', 'state_id')
    def _change_city_province(self):
        self.state_id = self.city_id.state_id.parent_id
        if self.state_id == self.env.ref('l10n_cl_counties.CL13'):
            self.city = 'Santiago'
        else:
            self.city = self.city_id.name


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _default_country(self):
        return self.env.ref('base.cl')

    city_id = fields.Many2one(
        "res.country.state.city", 'City',
        domain="[('country_id', '=', country_id)]")
    country_id = fields.Many2one(
        "res.country", 'Country',
        default=_default_country)

    @api.onchange('city_id', 'city', 'state_id')
    def _change_city_province(self):
        self.state_id = self.city_id.state_id.parent_id
        if self.state_id == self.env.ref('l10n_cl_counties.CL13'):
            self.city = 'Santiago'
        else:
            self.city = self.city_id.name
