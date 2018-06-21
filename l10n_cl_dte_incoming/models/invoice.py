# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging


_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = 'account.invoice'

    payment = fields.Text('Payment Term')
    document_type = fields.Integer('Document Type')
    document_number = fields.Integer('Document Number')

    @api.multi
    def set_default_values(self):
        """
        Sirve para setear los valores por defecto, antes o después de
        efectivamente generar la factura.
        Hay que garantizar:
        journal_id <- LIL
        document_number <- sii.dte.incoming.folio
        sii_document_number <- folio
        sii_document_class_id
        journal_document_class_id
        payment
        turn_issuer
        invoice_turn
        :return:
        """
        self.ensure_one()
        saorder_obj = self.env['sale.order']
        sale_order_id = saorder_obj.search([('name', '=', self.origin)])[0]
