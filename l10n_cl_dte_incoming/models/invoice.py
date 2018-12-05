# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging


_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = 'account.invoice'

    def invoice_id_dte_incoming_relationship(self):
        saorder_obj = self.env['sale.order']
        for record in self:
            if record.type not in ['out_invoice', 'out_refund'] and record.state not in ['open', 'paid']:
                _logger.info('registro %s descartado. Estado: %s, tipo: %s' % (record.id, record.state, record.type))
                continue
            for sale_order_id in saorder_obj.search([('name', '=', record.origin)]):
                _logger.info('registro %s procesando. Orden: %s, tipo: %s' % (record.id, sale_order_id.id, record.type))
                if sale_order_id.dte_inc_id[0] and not sale_order_id.dte_inc_id[0].invoice_id:
                    _logger.info('dte_incoming: %s' % sale_order_id.dte_inc_id[0].name)
                    sale_order_id.dte_inc_id[0].invoice_id = record.id
                    sale_order_id.dte_inc_id[0].flow_status = 'invoice'
                    _logger.info('registro %s se proceso a factura' % record.id)
                else:
                    _logger.info('registro %s ya procesado' % record.id)

    payment = fields.Text('Payment Term')
    document_type = fields.Integer('Document Type')

    @api.multi
    def action_invoice_open(self):
        saorder_obj = self.env['sale.order']
        for record in self:
            if record.type not in ['out_invoice', 'out_refund']:
                _logger.info('no out invoice o refund')
                super(Invoice, self).action_invoice_open()
                return False
            else:
                for sale_order_id in saorder_obj.search([('name', '=', record.origin)]):
                    # entrada normal
                    record.payment = sale_order_id.payment
                    record.document_type = sale_order_id.document_type
                    document_codes = {}
                    for documents in record.journal_id.journal_document_class_ids:
                        document_codes[documents.sii_document_class_id.sii_code] = documents.id
                    record.journal_document_class_id = document_codes[sale_order_id.document_type]
                    record.journal_document_class_id.sequence_id.number_next_actual = sale_order_id.document_number
                    record.turn_issuer = record.company_id.company_activities_ids[0]
                    # sale_order_id.dte_inc_id[0].invoice_id = record.id
                    # sale_order_id.dte_inc_id[0].flow_status = 'invoice'
                try:
                    super(Invoice, self).action_invoice_open()
                    return True
                except:
                    pass
                    return False

    def see_invoice(self):
        """
        Funcion para pruebas
        :return:
        """
        invoice = self.browse(3593)  # 20451
        for line in invoice.invoice_line_ids:
            _logger.info(line)
            for taxes in line.invoice_line_tax_ids:
                _logger.info(taxes)
        raise UserError('invoice')

    def reassing_account_invoice_lines_account(self):
        """
        Esta funcion está hecha para reasignar las cuentas contables obsoletas de las lineas en las facturas
        en estado borrador. Sirve para que estas se puedan validar, en caso que hayan sido generadas con cuentas
        del plan de cuentas que sean obsoletas
        :return:
        """
        conf = self.env['ir.config_parameter'].sudo()
        max_processed = int(conf.get_param('dte.sale.order.max.processed', default=30))
        _logger.info('will process %s' % max_processed)
        # records = self.search([('state', '=', 'draft')], order='id asc', limit=max_processed)
        records = self.search([('state', '=', 'draft')])
        for record in records:
            for line in record.invoice_line_ids:
                if line.account_id.id not in [570, 571]:
                    try:
                        if 'ALL / IN' in line.product_id.categ_id.display_name:
                            _logger.info('Reassing record: %s, product %s to 571' % (record.id, line.product_id.name))
                            line.account_id = self.env.ref('__export__.account_account_571')
                        else:
                            _logger.info('Reassing record: %s, product %s to 570' % (record.id, line.product_id.name))
                            line.account_id = self.env.ref('__export__.account_account_570')
                    except:
                        if not line.product_id.name:
                            _logger.info('Exception: record: %s, product false detected' % record.id)
                            continue
                        _logger.info('Exception: record: %s, product %s to 570' % (record.id, line.product_id.name))
                        line.account_id = self.env.ref('__export__.account_account_570')

    def action_invoice_open_multi1(self):
        conf = self.env['ir.config_parameter'].sudo()
        max_processed = int(conf.get_param('dte.sale.order.max.processed', default=30))
        i = 1
        _logger.info('seleccionadas %s facturas para validar' % len(self) or 0)
        for record in self:
            if record.state != 'draft':
                continue
            _logger.debug('Intentando validar factura: %s Folio: %s Para dte entrante: %s' % (
                record.id, record.document_number, i))
            try:
                record.action_invoice_open()
                _logger.info('Factura id: %s validada: %s, dte proc: %s' % (record.id, record.document_number, i))
                i += 1
                if i > max_processed:
                    return True
            except:
                return False
