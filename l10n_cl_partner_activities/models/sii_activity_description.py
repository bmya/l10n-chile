# -*- coding: utf-8 -*-
from odoo import models, fields


class PartnerActivities(models.Model):
    _description = 'SII Economical Activities Printable Description'
    _name = 'sii.activity.description'

    name = fields.Char('Glosa', required=True, translate=True)
    vat_affected = fields.Selection(
        [('SI', 'Si'), ('NO', 'No'), ('ND', 'ND')], 'VAT Affected',
        required=True, translate=True, default='SI')
    active = fields.Boolean(
        'Active', help="Allows you to hide the activity without removing it.",
        default=True)


class PartnerTurns(models.Model):
    _inherit = 'res.partner'

    activity_description = fields.Many2one(
        'sii.activity.description',
        string='Glosa Giro', ondelete="restrict")


class CompanyTurns(models.Model):
    _inherit = 'res.company'

    activity_description = fields.Many2one(
        string='Glosa Giro',
        related='partner_id.activity_description',
        relation='sii.activity.description')
