# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import base64
import xmltodict
from lxml import etree
import collections
import dicttoxml
import pysiidte
import json
from bs4 import BeautifulSoup as bs

_logger = logging.getLogger(__name__)

BC, EC = pysiidte.BC, pysiidte.EC


class IncomingDTE(models.Model):
    _name = 'sii.dte.incoming'
    _inherit = ['mail.thread']
    _description = 'Incoming DTEs Repository'

    def _track_subtype(self, init_values):
        if 'date_received' in init_values:
            return 'mail.mt_comment'
        return False

    @staticmethod
    def _get_xml_content(datas):
        return base64.b64decode(datas)
        #.decode('ISO-8859-1').replace(
        # '<?xml version="1.0" encoding="ISO-8859-1"?>', '')

    @api.onchange('name')
    def analyze_msg(self):
        # inspecciono los mensajes asociados
        for message_id in self.message_ids:
            _logger.info('Analizando mensaje: %s' % message_id.message_type)
            if message_id.message_type != 'email':
                # esto creo que es inutil, ya que en realidad debe buscar
                # archivos adjuntos y no mensajes
                _logger.info('busca otro mensaje porque este no tiene adj')
                continue
            self.date_received = message_id.date
            _logger.info('set de fecha de recepcion')
            for attachment_id in message_id.attachment_ids:
                _logger.info('hay attachment %s: ' % attachment_id)
                if not (attachment_id.mimetype in [
                    'text/plain'] and attachment_id.name.lower().find('.xml')):
                    _logger.info(u'El adjunto no es un XML. Revisando otro...')
                    continue
                _logger.info('El adjunto es un XML')
                xml = self._get_xml_content(attachment_id.datas)
                soup = bs(xml, 'xml')
                envio_dte = soup.find_all('EnvioDTE')
                qdte = soup.find_all('DTE')
                rta_dte = soup.find_all('RespuestaDTE')
                self.status = 'chk'
                if envio_dte and qdte:
                    if pysiidte.check_digest(xml):
                        self.check_envelope_status = 'in_envelope_ok'
                    else:
                        self.check_envelope_status = 'in_envelope_wrong'
                    self.type = 'in_dte'
                    coding = 'ISO-8859-1'
                    xmle = etree.fromstring(xml.decode(coding).replace(
                        '<?xml version="1.0" encoding="{}"?>'.format(coding),
                        ''))
                    if 'EnvioDTE' in xmle.tag:
                        for doc in xmle[0]:
                            if 'Caratula' in doc.tag:
                                continue
                            xmldoc = etree.tostring(doc)
                            if pysiidte.check_digest(xmldoc):
                                self.check_doc_status = 'in_dte_ok'
                            else:
                                self.check_doc_status = 'in_dte_wrong'
                elif rta_dte:
                    self.type = 'in_ack'

                elif 'DTE' in xmle.tag:
                    self.type = 'back'
                    pass
                # elif otros tipos..... (type)
#
#        """
#        # val = self.env['sii.dte.upload_xml.wizard'].create(vals)
#        # val.confirm()
#        """
#
    name = fields.Char('Nombre', track_visibility=True)
    date_received = fields.Datetime('Date and Time Received')
    type = fields.Selection([
        ('in_dte', 'DTE Proveedor'),
        ('in_ack', 'Acuse de Recibo Entrante'),
        ('in_acc', 'Acuse de Aceptación'),
        ('in_rec', 'Acuse de Recibo de Mercaderías'),
        ('back', 'Backup'),
        ('other', 'Otro')], string='Tipo')
    status = fields.Selection([
        ('new', 'New'),
        ('chk', 'Revisado'),
        ('ack', 'Acuse de Recibo'),
        ('acc', 'Aceptación Comercial'),
        ('rec', 'Acuse de Recepción de Mercaderías'), ], string='Estado',
        default='new',
        track_visibility=True)
    check_envelope_status = fields.Selection([
        ('in_envelope', 'Proveedor - Sobre sin verificar Documento'),
        ('in_envelope_wrong', 'Proveedor - Sobre Firma Incorrecta'),
        ('in_envelope_ok', 'Proveedor - Sobre Verificado'), ],
        string='Verif Sobre')
    check_doc_status = fields.Selection([
        ('in_dte', 'DTE Proveedor - Sin verificar Documento'),
        ('in_dte_wrong', 'DTE Proveedor - Documento Firma Incorrecta'),
        ('in_dte_ok', 'DTE Proveedor - Documento Verificada Firma'), ],
        string='Verif DOC')
    partner_id = fields.Many2one(
        'res.partner', string='Partner', track_visibility=True)
    filename = fields.Char('File Name')
    invoice_id = fields.Many2one(
        'account.invoice', invisible=True, track_visibility=True)
