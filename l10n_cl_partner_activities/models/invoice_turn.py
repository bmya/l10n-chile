# -*- coding: utf-8 -*-
from odoo import models, fields, api


class invoice_turn(models.Model):
    _inherit = "account.invoice"

    def set_partner_activity(self):
        for default_activity in self.partner_id.partner_activities_ids:
            return default_activity

    invoice_turn = fields.Many2one(
        'partner.activities',
        'Giro',
        readonly=True,
        default=set_partner_activity,
        store=True,
        states={'draft': [('readonly', False)]})
    activity_description = fields.Many2one(
        'sii.activity.description',
        string="Giro",
        related="partner_id.activity_description",
        readonly=True)

    @api.onchange('partner_id')
    def _set_default_activity(self):
        self.invoice_turn = self.set_partner_activity()




