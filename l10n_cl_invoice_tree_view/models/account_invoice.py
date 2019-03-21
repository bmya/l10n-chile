# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountInvoiceTree(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    document_code = fields.Char(related='document_class_id.code', string="Doc Type")
    vat_id = fields.Char(related='partner_id.document_number', string="RUT")
    amount_untaxed_signed = fields.Monetary(compute='_get_amount_signed', string='Net Amount')
    amount_tax_signed = fields.Monetary(compute='_get_amount_signed', string='Net Amount')

    @api.depends('amount_total_signed')
    def _get_amount_signed(self):
        for record in self:
            factor = 1 if record.amount_total_signed >= 0 else -1
            record.amount_untaxed_signed = record.amount_untaxed * factor
            record.amount_tax_signed = record.amount_tax * factor
