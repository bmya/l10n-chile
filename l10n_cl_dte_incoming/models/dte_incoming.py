# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import base64
from lxml import etree
import pysiidte
import collections
import dicttoxml, xmltodict
from datetime import datetime
from bs4 import BeautifulSoup as bs
import pytz
import json


_logger = logging.getLogger(__name__)

BC, EC = pysiidte.BC, pysiidte.EC


class IncomingDTE(models.Model):
    _name = 'sii.dte.incoming'
    _inherit = 'mail.thread'
    _description = 'Incoming DTEs Repository'

    @staticmethod
    def _track_subtype(init_values):
        if 'date_received' in init_values:
            return 'mail.mt_comment'
        return False

    @staticmethod
    def _get_xml_content(datas):
        return base64.b64decode(datas)

    def get_incoming_dte_attachment(self):
        # en este caso, el attachment no está en el mensaje adjunto sino
        # adjunto al registro.
        _logger.info('revisando el adjunto del entrante: %s' % self.id)
        attachment_obj = self.env['ir.attachment'].sudo()
        attachment_ids = attachment_obj.search([
            ('res_model', '=', 'sii.dte.incoming'),
            ('res_id', '=', self.id), ])
        _logger.info('Found attachments: %s' % attachment_ids)
        return [base64.b64decode(att_id.datas) for att_id in attachment_ids]

    def create_sale_partner(self, partner_obj, receptor):
        customer = {
            'vat': 'CL' + receptor.RUTRecep.text.replace('-', ''),
            'name': receptor.RznSocRecep.text,
            'street': receptor.DirRecep.text,
        }
        partner_id = partner_obj.create(customer)
        _logger.info('creacion de nuevo cliente: %s' % json.dumps(customer))
        return partner_id

    def get_product_id(self, product_obj, default_code):
        try:
            product = product_obj.search(
                [('default_code', '=', default_code)])[0].id
            return product
        except IndexError:
            raise UserError(
                'El producto %s no existe en el sistema' % default_code)

    def format_sale_order(self, saorder_obj, partner_id, detail, warehouse_id):
        order_dict = {
            'partner_id': partner_id.id,
            'origin': 'idn',
            'warehouse_id': warehouse_id.id,
        }
        product_obj = self.env['product.product']
        lines = [(5, )]
        for product_line in detail:
            _logger.info('product_line: %s' % product_line)
            name_code = product_line.NmbItem.text.split(' ')
            line = {
                'product_id': self.get_product_id(
                    product_obj, name_code[0]),
                'name': ' '.join(name_code[:1]),
                'product_uom_qty': product_line.QtyItem.text,
                'price_unit': product_line.PrcItem.text
            }
            _logger.info(line)
            lines.append((0, 0, line))
        order_dict['order_line'] = lines
        _logger.info('Orden dictionary: %s' % order_dict)
        order_new = saorder_obj.create(order_dict)
        _logger.info('Orden Creada: %s' % order_new.id)
        orden_creada = {
            'order_id': order_new.id,
            'order_name': order_new.name,
            'status': order_new.state,
            'origin': order_new.origin
        }
        _logger.info(orden_creada)
        return order_new

    def _choose_warehouse(self):
        warehouse_name = self.name.split(' ')[0]
        stock_wh_obj = self.env['stock.warehouse']
        stock_wh_name = stock_wh_obj.search([
            ('code', '=', warehouse_name)])
        return stock_wh_name

    def _choose_workflow(self):
        workflow_name = self.name.split(' ')[0]
        stock_wf_obj = self.env['sale.workflow.process']
        stock_wf_name = stock_wf_obj.search([
            ('name', 'ilike', workflow_name)])
        return stock_wf_name

    def create_sale_order(self):
        for x in self:
            if x.type == 'out_dte':
                partner_obj = x.env['res.partner']
                product_obj = x.env['product.product']
                try:
                    saorder_obj = x.env['sale.order']
                except KeyError:
                    raise UserError('Debe instalar el modulo Sales')
                _logger.info('create_sale_order, out_dte record: %s' % x.id)
                incoming_dtes = x.get_incoming_dte_attachment()
                for inc_dte in incoming_dtes:
                    bsoup = bs(inc_dte, 'xml')
                    _logger.info('RUTRecep: %s' % bsoup.RUTRecep.text)
                    try:
                        partner_id = partner_obj.search(
                            [('vat', '=',
                              'CL' + bsoup.RUTRecep.text.replace(
                                  '.', '').replace('-', ''))])[0]
                        _logger.info('partner_id: %s' % partner_id)
                    except IndexError:
                        _logger.info('El vat no se encuentra en bdd')
                        partner_id = x.create_sale_partner(
                            partner_obj, bsoup.Receptor)
                    detail = bsoup.find_all('Detalle')
                    warehouse_id = x._choose_warehouse()
                    workflow_id = x._choose_workflow()
                    order_new = x.format_sale_order(
                        saorder_obj, partner_id, detail, warehouse_id)
                    _logger.info(detail)
                    _logger.info(order_new)
                    x.write({
                        'partner_id': partner_id.id,
                        'flow_status': 'order',
                        'sale_order_id': order_new.id,
                        'warehouse_id': warehouse_id.id,
                        'workflow_process_id': workflow_id.id,
                    })
                    order_new.action_confirm()
                    # la orden de confirmación se cambia a la hora real.
                    order_new.write({'confirmation_date': x.date_received})
                    # mandar el tipo de dte, folio y fecha de la factura
                    # crear la factura
                    # asignar fecha y folio correcto
                    # rebajar el inventario de la tienda que corresponda.
                    # usar el diario correcto de venta sucursal.

            else:
                _logger.info('create_sale_order, not out_dte: %s' % x.id)

    @api.onchange('name')
    def analyze_msg(self):
        # inspecciono los mensajes asociados
        for message_id in self.message_ids:
            _logger.info('Analizando mensaje: %s' % message_id.message_type)
            if message_id.message_type != 'email':
                # esto creo que es inutil, ya que en realidad debe buscar
                # archivos adjuntos y no mensajes
                # nota de Daniel: no es inútil porque el adjunto está
                # relacionado al email adjunto y no directamente al registro.
                _logger.info('busca otro mensaje porque este no tiene adj')
                continue
            self.date_received = message_id.date
            _logger.info('set de fecha de recepcion')
            for attachment_id in message_id.attachment_ids:
                _logger.info('hay attachment %s: ' % attachment_id)
                if not (attachment_id.mimetype in ['text/plain'] and
                        attachment_id.name.lower().find('.xml')):
                    _logger.info(u'El adjunto no es un XML. Revisando otro...')
                    continue
                _logger.info('El adjunto es un XML')
                xml = self._get_xml_content(attachment_id.datas)
                soup = bs(xml, 'xml')  # se crea un arbol de xml
                envio_dte = soup.find_all('EnvioDTE')  # busqueda
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
    name = fields.Char('Nombre', track_visibility='onchange')
    date_received = fields.Datetime('Date and Time Received')
    type = fields.Selection([
        ('out_dte', 'DTE Ventas'),
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
        track_visibility='onchange')
    flow_status = fields.Selection([
        ('new', 'New'),
        ('order', 'Order'),
        ('draft', 'Draft Invoice'),
        ('invoice', 'Invoice Created'), ], string='Estado Flujo',
        default='new',
        help='Status related to Odoo sale or purchase flow',
        track_visibility='onchange')
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
        'res.partner', string='Partner', track_visibility='onchange')
    filename = fields.Char('File Name')
    purchase_order_id = fields.Many2one(
        'purchase.order', track_visibility='onchange')
    sale_order_id = fields.Many2one(
        'sale.order', track_visibility='onchange')
    invoice_id = fields.Many2one(
        'account.invoice', track_visibility='onchange')
    sii_xml_merchandise = fields.Text('SII Merchandise')
    sii_xml_request = fields.Text('SII Request')
    sii_xml_accept = fields.Text('SII Accept')
    name_xml = fields.Char('Name xml')
    payment = fields.Text('Payment Terms')

    @api.multi
    def receive_merchandise(self):
        # date = pysiidte.time_stamp()
        inv_obj = self.env['account.invoice']

        for message_id in self.message_ids:
            for attachment_id in message_id.attachment_ids:
                # if not (attachment_id.mimetype in [
                #    'text/plain'] and attachment_id.name.lower().find('.xml')):
                #    _logger.info(u'El adjunto no es un XML. Revisando otro...')
                #     continue
                _logger.info('El adjunto es un XML')
                xml = self._get_xml_content(attachment_id.datas)
                soup = bs(xml, 'xml')  # se crea un arbol de xml
                libro_guia = soup.find_all('EnvioDTE')  # busqueda

                if libro_guia:
                    signature_d = inv_obj.get_digital_signature(
                        self.env.user.company_id)
                    certp = signature_d['cert'].replace(
                        BC, '').replace(EC, '').replace('\n', '')
                    date = pysiidte.time_stamp()
                    caratula = collections.OrderedDict()
                    caratula['RutResponde'] = '{}'.format(soup.RUTRecep.string)
                    caratula['RutRecibe'] = '{}'.format(soup.RUTEmisor.string)
                    caratula['NmbContacto'] = self.env.user.partner_id.name
                    caratula['FonoContacto'] = self.env.user.partner_id.phone
                    caratula['MailContacto'] = self.env.user.partner_id.email
                    caratula['TmstFirmaEnv'] = date
                    caratula_xml = dicttoxml.dicttoxml(
                        caratula, root=False, attr_type=False)
                    merchandise = collections.OrderedDict()
                    merchandise['TipoDoc'] = int(soup.TipoDTE.string)
                    merchandise['Folio'] = int(soup.Folio.string)
                    merchandise['FchEmis'] = '{}'.format(soup.FchEmis.string)
                    merchandise['RUTEmisor'] = '{}'.format(
                        soup.RUTEmisor.string)
                    merchandise['RUTRecep'] = '{}'.format(soup.RUTRecep.string)
                    merchandise['MntTotal'] = int(soup.MntTotal.string)
                    merchandise['Recinto'] = self.env.user.company_id.street
                    merchandise['RutFirma'] = signature_d[
                        'subject_serial_number']
                    merchandise['Declaracion'] = '''El acuse de recibo que \
se declara en este acto, de acuerdo a lo dispuesto en la letra b) del Art. 4, \
y la letra c) del Art. 5 de la Ley 19.983, acredita que la entrega de \
mercaderias o servicio(s) prestado(s) ha(n) sido recibido(s).'''
                    merchandise['TmstFirmaRecibo'] = date
                    merchandise_xml = dicttoxml.dicttoxml(
                                merchandise,
                                root=False,
                                attr_type=False, )
                    dicttoxml.set_debug(False)
                    id = "T" + str(soup.TipoDTE.string) + "F" + str(
                        soup.Folio.string)
                    doc = '''<Recibo version="1.0" \
xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte Recibos_v10.xsd">
                        <DocumentoRecibo ID="{0}" >
                        {1}
                        </DocumentoRecibo>
                    </Recibo>
                    '''.format(id, merchandise_xml)
                    recibo_merca = inv_obj.sign_full_xml(
                        doc, signature_d['priv_key'],
                        inv_obj.split_cert(certp), 'Recibo', 'recep')
                    xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
                    <EnvioRecibos xmlns='http://www.sii.cl/SiiDte' \
xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' \
xsi:schemaLocation='http://www.sii.cl/SiiDte EnvioRecibos_v10.xsd' \
version="1.0">
                        <SetRecibos ID="SetDteRecibidos">
                            <Caratula version="1.0">
                            {0}
                            </Caratula>
                            {1}
                        </SetRecibos>
                    </EnvioRecibos>'''.format(caratula_xml, recibo_merca)
                    envio_dte = inv_obj.sign_full_xml(
                        xml, signature_d['priv_key'], certp, 'SetDteRecibidos',
                        'env_recep')
                    
                    self.save_xml_knowledge(
                        envio_dte, 'merchandise_{}'.format(id))
                    self.sii_xml_merchandise = envio_dte

    @api.multi
    def document_received(self):
        date = pysiidte.time_stamp()
        inv_obj = self.env['account.invoice']

        for message_id in self.message_ids:
            for attachment_id in message_id.attachment_ids:
                # if not (attachment_id.mimetype in [
                #    'text/plain'] and attachment_id.name.lower().find('.xml')):
                #    _logger.info(u'El adjunto no es un XML. Revisando otro...')
                #    continue
                _logger.info('El adjunto es un XML')
                xml = self._get_xml_content(attachment_id.datas)
                soup = bs(xml, 'xml')  # se crea un arbol de xml
                envio_dte = soup.find_all('EnvioDTE')  # busqueda

                if envio_dte:
                    # signature_d = inv_obj.get_digital_signature(
                    # self.env.user.company_id)
                    try:
                        signature_d = inv_obj.get_digital_signature(
                            self.env.user.company_id)
                    except:
                        raise UserError(_('''There is no Signer Person with \
an authorized signature for you in the system. Please make sure that \
'user_signature_key' module has been installed and enable a digital \
signature, for you or make the signer to authorize you to use his \
signature.'''))
                    certp = signature_d['cert'].replace(
                        BC, '').replace(EC, '').replace('\n', '')
                    tz = pytz.timezone('America/Santiago')
                    day = datetime.now(tz).strftime('%y%d%H%M')
                    idrespuesta = day
                    caratula = collections.OrderedDict()
                    caratula['RutResponde'] = '{}'.format(
                        soup.RutReceptor.string)
                    caratula['RutRecibe'] = '{}'.format(
                        soup.RUTEmisor.string)
                    caratula['IdRespuesta'] = idrespuesta
                    caratula['NroDetalles'] = 1
                    caratula['TmstFirmaResp'] = date

                    caratula_xml = dicttoxml.dicttoxml(
                        caratula, root=False, attr_type=False)
                    fecha = datetime.strptime(
                        message_id.date, '%Y-%m-%d %H:%M:%S').strftime(
                        '%Y-%m-%dT%H:%M:%S')
                    RecepcionEnvio = collections.OrderedDict()
                    RecepcionEnvio['NmbEnvio'] = '{}'.format(attachment_id.name)
                    RecepcionEnvio['FchRecep'] = fecha
                    RecepcionEnvio['CodEnvio'] = idrespuesta
                    RecepcionEnvio['EnvioDTEID'] = soup.Documento['ID']
                    # soup.SetDTE['ID']
                    RecepcionEnvio['Digest'] = '{}'.format(
                        soup.DigestValue.string)
                    RecepcionEnvio['RutEmisor'] = '{}'.format(
                        soup.RUTEmisor.string)
                    RecepcionEnvio['RutReceptor'] = '{}'.format(
                        soup.RUTRecep.string)
                    RecepcionEnvio['EstadoRecepEnv'] = '0'
                    RecepcionEnvio['RecepEnvGlosa'] = 'Envio Recibido Conforme'

                    recepcionenvio_xml = dicttoxml.dicttoxml(
                                RecepcionEnvio,
                                root=False,
                                attr_type=False,
                            )
                    dicttoxml.set_debug(False)
                    xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
                    <RespuestaDTE xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0" \
xsi:schemaLocation="http://www.sii.cl/SiiDte RespuestaEnvioDTE_v10.xsd">
                        <Resultado ID="Odoo_resp">
                            <Caratula version="1.0">
                                {0}
                            </Caratula>
                            <RecepcionEnvio>
                                {1}
                            </RecepcionEnvio>
                        </Resultado>
                    </RespuestaDTE>
                    '''.format(caratula_xml, recepcionenvio_xml)
                    acuse_recibo = inv_obj.sign_full_xml(
                        xml, signature_d['priv_key'],
                        inv_obj.split_cert(certp), 'Odoo_resp', 'env_resp')
                    _logger.info('estamos por crear')
                    self.save_xml_knowledge(
                        acuse_recibo, 'received_{}'.format(idrespuesta))
                    self.sii_xml_request = acuse_recibo

    @api.multi
    def commercial_acceptance(self):
        date = pysiidte.time_stamp()
        inv_obj = self.env['account.invoice']

        for message_id in self.message_ids:
            for attachment_id in message_id.attachment_ids:
                # if not (attachment_id.mimetype in [
                #     'text/plain'] and attachment_id.name.lower().find(
                # '.xml')):
                #     _logger.info(u'El adjunto no es un XML.
                # Revisando otro...')
                #     continue
                _logger.info('El adjunto es un XML')
                xml = self._get_xml_content(attachment_id.datas)
                soup = bs(xml, 'xml')  # se crea un arbol de xml
                envio_dte = soup.find_all('EnvioDTE')  # busqueda

                if envio_dte:
                    signature_d = inv_obj.get_digital_signature(
                        self.env.user.company_id)
                    
                    certp = signature_d['cert'].replace(
                        BC, '').replace(EC, '').replace('\n', '')

                    tz = pytz.timezone('America/Santiago')
                    day = datetime.now(tz).strftime('%y%d%H%M')
                    idrespuesta = day

                    caratula = collections.OrderedDict()
                    caratula['RutResponde'] = '{}'.format(
                        soup.RutReceptor.string)
                    caratula['RutRecibe'] = '{}'.format(
                        soup.RUTEmisor.string)
                    caratula['IdRespuesta'] = idrespuesta
                    caratula['NroDetalles'] = 1
                    caratula['NmbContacto'] = self.env.user.name
                    caratula['FonoContacto'] = self.env.user.partner_id.phone
                    caratula['MailContacto'] = self.env.user.partner_id.email
                    caratula['TmstFirmaResp'] = date

                    caratula_xml = dicttoxml.dicttoxml(
                                caratula, root=False, attr_type=False)
                    apectacionComercial = collections.OrderedDict()
                    apectacionComercial['TipoDTE'] = '{}'.format(
                        soup.TipoDTE.string)
                    apectacionComercial['Folio'] = '{}'.format(
                        soup.Folio.string)
                    apectacionComercial['FchEmis'] = '{}'.format(
                        soup.FchEmis.string)
                    apectacionComercial['RUTEmisor'] = '{}'.format(
                        soup.RUTEmisor.string)
                    apectacionComercial['RUTRecep'] = '{}'.format(
                        soup.RUTRecep.string)
                    apectacionComercial['MntTotal'] = int(
                        soup.MntTotal.string)
                    apectacionComercial['CodEnvio'] = idrespuesta
                    apectacionComercial['EstadoDTE'] = 0
                    apectacionComercial['EstadoDTEGlosa'] = ''

                    _logger.info(apectacionComercial)

                    aceptacion_xml = dicttoxml.dicttoxml(
                                apectacionComercial,
                                root=False,
                                attr_type=False,
                            )

                    dicttoxml.set_debug(False)
                    xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
                    <RespuestaDTE xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
version="1.0" xsi:schemaLocation="http://www.sii.cl/SiiDte \
RespuestaEnvioDTE_v10.xsd">
                        <Resultado ID="Odoo_resp">
                            <Caratula version="1.0">
                                {0}
                            </Caratula>
                            <ResultadoDTE>
                                {1}
                            </ResultadoDTE>
                        </Resultado>
                    </RespuestaDTE>
                    '''.format(caratula_xml, aceptacion_xml)

                    aceptacion_comercial = inv_obj.sign_full_xml(
                        xml, signature_d['priv_key'],
                        inv_obj.split_cert(certp), 'Odoo_resp', 'env_resp')

                    self.save_xml_knowledge(
                        aceptacion_comercial, 'acceptance_{}'.format(
                            idrespuesta))
                    self.sii_xml_accept = aceptacion_comercial
                    attachment = self.env['ir.attachment'].search(
                        [('res_model', '=', 'sii.dte.incoming'),
                         ('res_id', '=', self.id)])
                    file_name = attachment[0].name
                    result = inv_obj.send_xml_file(
                        aceptacion_comercial, file_name,
                        self.env.user.company_id)
                    _logger.info('Enviado: %s' % result)

    @api.multi
    def save_xml_knowledge(self, document, file_name):
        attachment_obj = self.env['ir.attachment']
        _logger.info('Attachment')
        for inv in self:
            name = 'DTE_{}.xml'.format(
                file_name).replace(' ', '_')
            inv.name_xml = name
            attachment_id = attachment_obj.create(
                {
                    'name': name,
                    'datas': base64.b64encode(document),
                    'datas_fname': name,
                    'res_model': inv._name,
                    'res_id': inv.id,
                    'type': 'binary', })
            _logger.info('Se ha generado XML con el id {}'.format(
                attachment_id))

    # def get_xml_file(self):
    #     """
    #    Funcion para descargar el attachmnet en el sistema local del usuario
    #     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    #     @version: 2016-05-01
    #    """
    #    return {
    #        'type': 'ir.actions.act_url',
    #        'url': '/web/binary/download_document?model=sii.dte.incoming&\
    # field=sii_xml_request&id=%s&filename=%s' % (self.id,self.name_xml),
    #        'target': 'self', }

    @api.multi
    def send_xml_file_button(self):
        company_id = self.env.user.company_id
        inv = self.env['account.invoice']
        # signature_d = inv.get_digital_signature(self.env.user.company_id)
        attachment = self.env['ir.attachment'].search(
            [('res_model', '=', 'sii.dte.incoming'), ('res_id', '=', self.id)])
        file_name = attachment[0].name
        result = inv.send_xml_file(self.sii_xml_request, file_name, company_id)
        _logger.info('result {}'.format(result))

    @api.multi
    def send_xml_merchandise_button(self):
        company_id = self.env.user.company_id
        inv = self.env['account.invoice']
        attachment = self.env['ir.attachment'].search(
            [('res_model', '=', 'sii.dte.incoming'), ('res_id', '=', self.id)])
        file_name = attachment[0].name
        result = inv.send_xml_file(
            self.sii_xml_merchandise, file_name, company_id)
        _logger.info('result {}'.format(result))

    @api.multi
    def send_xml_accept_button(self):
        company_id = self.env.user.company_id
        inv = self.env['account.invoice']
        attachment = self.env['ir.attachment'].search(
            [('res_model', '=', 'sii.dte.incoming'), ('res_id', '=', self.id)])
        file_name = attachment[0].name
        result = inv.send_xml_file(self.sii_xml_accept, file_name, company_id)
        _logger.info('result {}'.format(result))
