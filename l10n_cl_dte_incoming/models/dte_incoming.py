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
        return base64.b64decode(datas).decode('ISO-8859-1').replace(
            '<?xml version="1.0" encoding="ISO-8859-1"?>', '')

    @api.onchange('name')
    def analyze_msg(self):
        # inspecciono los mensajes asociados
        for message_id in self.message_ids:
            if message_id.message_type == 'email':
                self.date_received = message_id.date
                for attachment_id in message_id.attachment_ids:
                    if attachment_id:
                        _logger.info('hay attachment %s: ' % attachment_id)
                        if attachment_id.mimetype in [
                            'text/plain'] and \
                                attachment_id.name.lower().find('.xml'):
                            _logger.info('El adjunto es un XML')
                            xml = self._get_xml_content(attachment_id.datas)
                            if not pysiidte.check_digest(xml):
                                _logger.info(u'Error de firma en envío')
                                return False
                            soup = bs(xml, 'xml')
                            for sending in soup.find_all('SetDTE'):
                                # _logger.info(sending)
                                dte_qty = 0
                                for docs in sending.find_all('DTE'):
                                    dte_qty += 1
                                    if not self._check_digest(docs):
                                        _logger.info(u'Error de firma en uno \
                                        de los documentos')
                                        return False


                            # aca tengo que investigar que tipo de xml es

        """
        # val = self.env['sii.dte.upload_xml.wizard'].create(vals)
        # val.confirm()
        """

    name = fields.Char('Nombre', track_visibility=True)
    date_received = fields.Datetime('Date and Time Received')
    status = fields.Selection([
        ('new', 'New'),
        ('ack', 'Acuse de Recibo'),
        ('acc', 'Aceptación Comercial'),
        ('rec', 'Acuse de Recepción de Mercaderías'), ], string='Estado',
        default='new',
        track_visibility=True)
    type = fields.Selection([
        ('in_dte', 'DTE Proveedor'),
        ('in_ack', 'Recibo Entrante'),
        ('in_acc', 'Recibo de Aceptación'),
        ('in_rec', 'Recibo de Mercaderías'),
        ('back', 'Backup'),
        ('other', 'Otro')], string='Tipo')
    partner_id = fields.Many2one(
        'res.partner', string='Partner', track_visibility=True)
    filename = fields.Char('File Name')
    invoice_id = fields.Many2one(
        'account.invoice', invisible=True, track_visibility=True)
