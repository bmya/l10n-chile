# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""
    _inherit = "account.invoice.refund"

    tipo_nota = fields.Many2one(
        'sii.document_class', string="Tipo De nota", required=True,
        domain=[
            ('document_type', 'in', ['debit_note', 'credit_note']),
            ('dte', '=', True), ])
    filter_refund = fields.Selection([
                ('1', 'Anula Documento de Referencia'),
                ('2', 'Corrige texto Documento Referencia'),
                ('3', 'Corrige montos')], default='1', string='Refund Method',
        required=True,
        help='Refund base on this type. You can not Modify and Cancel if the \
invoice is already reconciled')
