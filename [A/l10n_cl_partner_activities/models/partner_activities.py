# -*- coding: utf-8 -*-
from odoo import models, fields


class PartnerActivities(models.Model):
    _description = 'SII Economical Activities'
    _name = 'partner.activities'

    code = fields.Char('Activity Code', required=True, translate=True)
    parent_id = fields.Many2one(
        'partner.activities', 'Parent Activity', ondelete='cascade')
    name = fields.Char('Nombre Completo', required=True, translate=True)
    vat_affected = fields.Selection(
        [('SI', 'Si'), ('NO', 'No'), ('ND', 'ND')], 'VAT Affected',
        required=True, translate=True, default='SI')
    tax_category = fields.Selection(
        [('1', '1'), ('2', '2'), ('ND', 'ND')], 'TAX Category', required=True,
        translate=True, default='1')
    internet_available = fields.Boolean('Available at Internet', default=True)
    active = fields.Boolean(
        'Active', help="Allows you to hide the activity without removing it.",
        default=True)
    partner_ids = fields.Many2many(
        'res.partner', id1='activities_id', id2='partner_id',
        string='Partners')


class PartnerTurns(models.Model):
    _description = 'Partner registered turns'
    _inherit = 'res.partner'

    partner_activities_ids = fields.Many2many(
        'partner.activities', id1='partner_id', id2='activities_id',
        string='Activities Names', translate=True,
        help=u'Seleccione las actividades económicas registradas en el SII')


class CompanyTurns(models.Model):

    _description = 'Company registered turns'
    _inherit = 'res.company'

    company_activities_ids = fields.Many2many(
        string='Activities Names',
        related='partner_id.partner_activities_ids',
        relation='partner.activities',
        help=u'Seleccione las actividades económicas registradas en el SII')
