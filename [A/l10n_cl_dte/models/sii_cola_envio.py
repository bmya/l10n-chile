# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import logging
import ast

_logger = logging.getLogger(__name__)


class ColaEnvio(models.Model):
    _name = "sii.cola_envio"

    doc_ids = fields.Char(string="Id Documentos")
    model = fields.Char(string="Model destino")
    user_id = fields.Many2one('res.users')
    tipo_trabajo = fields.Selection(
        [('envio', 'Envío'),
         ('consulta', 'Consulta'),
         ('rechazado', 'Rechazado')],
        string='Tipo de trabajo')
    active = fields.Boolean(string="Active", default=True)
    att_number = fields.Char(string="Número de atención")
    xml_sending = fields.Text(string="XML Sending SII")

    @api.model
    def _cron_process_queue(self):
        _logger.info(u'Ingreso en la cola de envío')
        ids = self.search([('active', '=', True)])
        if ids:
            _logger.info(
                u'Se encontraron registros para procesar: {}'.format(ids))
            for c in ids:
                _logger.info(u'Procesando registros de {} ids: {}'.format(
                    c.model, c.doc_ids))
                list_invoices = ast.literal_eval(c.doc_ids)
                list_invoices.sort()
                docs = self.env[c.model].browse(list_invoices)
                if docs[0].sii_send_ident and docs[0].sii_message and \
                        docs[0].sii_result in [
                            'Rechazado', 'Aceptado']:
                    _logger.info(u'El primer registro del grupo se encuentra \
en estado: {}. Se descarta el envío de este grupo. No se consultará nuevamente\
 por cola'.format(docs[0].sii_result))
                    c.active = False
                    # c.unlink()
                    # return
                else:
                    _logger.info(
                        u'Comenzando el proceso de envío para {}'.format(docs))
                    for doc in docs:
                        doc.responsable_envio = c.user_id
                    if c.tipo_trabajo == 'envio':
                        _logger.info(
                            u'Realizando Envío de {} para nro atención: \
{}'.format(docs, c.att_number))
                        c.xml_sending = docs.do_dte_send(c.att_number)
                        c.tipo_trabajo = 'consulta'
                    elif c.tipo_trabajo == 'consulta':
                        _logger.info(u'Realizando consulta para {}'.format(
                            docs))
                        docs[0].ask_for_dte_status()
        else:
            _logger.info(u'NO se encontraron ids para enviar')

    @api.model
    def _cron_check_inprocess_invoices(self):
        _logger.info(u'Buscando comprobantes en proceso...')
        inv_obj = self.env['account.invoice']
        inprocess_ids = inv_obj.search([
            ('sii_result', 'in', ['Enviado', 'Proceso'])])
        for inprocess_id in inprocess_ids:
            _logger.info(u'Procesando invoice id: {}', format(inprocess_id))
            inprocess_id.ask_for_dte_status()
