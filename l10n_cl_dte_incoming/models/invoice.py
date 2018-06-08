# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging


_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = 'account.invoice'

    def _get_document_type_from_journal(self, sale_order_id):
        _logger.info('\n\n\n\n\nget document type from journal\n\n\n\n\n')
        dci = self.env['sii.document_class']
        dci_id = dci.search([
            ('sii_code', '=', sale_order_id.document_type)
        ])[0]
        """
        journal_document_class_id = self.journal_id.search(
            [
                ()
            ]
        )"""
        return dci_id, 0

    payment = fields.Text('Payment Term')  # <- JSON payment
    document_type = fields.Integer('Document Type')  # <- sii.inc.dte.TipoDoc
    document_number = fields.Integer('Document Number')  # <- sii.inc.dte.Folio

    @api.model
    def create(self, vals):
        _logger.info('\n\n\n\n\ncreate invoice from dte_incoming\n\n\n\n\n')
        record = super(Invoice, self).create(vals)
        """
        saorder_obj = self.env['sale.order']
        sale_order_id = saorder_obj.search([('name', '=', record.origin)])[0]
        record.payment = sale_order_id.payment
        record.sii_document_class_id = self._get_document_type_from_journal(sale_order_id)[0]
        record.journal_document_class_id = self._get_document_type_from_journal(sale_order_id)[1]
        record.sii_document_number = sale_order_id.document_number
        """

