# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging


_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = 'account.invoice'

    payment = fields.Text('Payment Term')
    document_type = fields.Integer('Document Type')

    @api.multi
    def action_invoice_open(self):
        saorder_obj = self.env['sale.order']
        for record in self:
            if record.type not in ['out_invoice', 'out_refund']:
                continue
            for sale_order_id in saorder_obj.search([('name', '=', record.origin)]):
                record.payment = sale_order_id.payment
                record.document_type = sale_order_id.document_type
                document_codes = {}
                for documents in record.journal_id.journal_document_class_ids:
                    document_codes[documents.sii_document_class_id.sii_code] = documents.id
                record.journal_document_class_id = document_codes[sale_order_id.document_type]
                record.journal_document_class_id.sequence_id.number_next_actual = sale_order_id.document_number
                record.turn_issuer = record.company_id.company_activities_ids[0]
                sale_order_id.dte_inc_id[0].invoice_id = record.id
                sale_order_id.dte_inc_id[0].flow_status = 'invoice'
                break
        super(Invoice, self).action_invoice_open()
