# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from lxml import etree
import logging
import json
import collections
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
try:
    from suds.client import Client
except:
    pass
try:
    import urllib3
except:
    pass
pool = urllib3.PoolManager(timeout=30)

_logger = logging.getLogger(__name__)

try:
    import xmltodict
except ImportError:
    _logger.info('Cannot import xmltodict library')

try:
    import dicttoxml
    dicttoxml.set_debug(False)
except ImportError:
    _logger.info('Cannot import dicttoxml library')

try:
    from elaphe import barcode
except ImportError:
    _logger.info('Cannot import elaphe library')

try:
    import M2Crypto
except ImportError:
    _logger.info('Cannot import M2Crypto library')

try:
    import base64
except ImportError:
    _logger.info('Cannot import base64 library')

try:
    import hashlib
except ImportError:
    _logger.info('Cannot import hashlib library')

try:
    import cchardet
except ImportError:
    _logger.info('Cannot import cchardet library')

try:
    from SOAPpy import SOAPProxy
except ImportError:
    _logger.info('Cannot import SOOAPpy')

try:
    from signxml import XMLSigner, XMLVerifier, methods
except ImportError:
    _logger.info('Cannot import signxml')
import xml.dom.minidom


server_url = {
    'SIIHOMO': 'https://maullin.sii.cl/DTEWS/',
    'SII':'https://palena.sii.cl/DTEWS/', }

BC = '''-----BEGIN CERTIFICATE-----\n'''
EC = '''\n-----END CERTIFICATE-----\n'''

import os
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace(
    '/models', '/static/xsd/')

connection_status = {
    '0': 'Upload OK',
    '1': 'El Sender no tiene permiso para enviar',
    '2': 'Error en tamaño del archivo (muy grande o muy chico)',
    '3': 'Archivo cortado (tamaño <> al parámetro size)',
    '5': 'No está autenticado',
    '6': 'Empresa no autorizada a enviar archivos',
    '7': 'Esquema Invalido',
    '8': 'Firma del Documento',
    '9': 'Sistema Bloqueado',
    'Otro': 'Error Interno.', }


def to_json(colnames, rows):
    all_data = []
    for row in rows:
        each_row = collections.OrderedDict()
        i = 0
        for colname in colnames:
            each_row[colname] = row[i]
            i += 1
        all_data.append(each_row)
    return all_data


def db_handler(method):
    def call(self, *args, **kwargs):
        _logger.info(args)
        account_invoice_ids = [str(x.id) for x in self.invoice_ids]
        query = method(self, *args, **kwargs)
        cursor = self.env.cr
        cursor.execute(query % ', '.join(account_invoice_ids))
        rows = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        _logger.info('colnames: {}'.format(colnames))
        _logger.info('rows: {}'.format(rows))
        return to_json(colnames, rows)
    return call


class AccountMoveBook(models.Model):
    _name = "account.move.book"

    sii_receipt = fields.Text(
        string='SII Message',
        copy=False)
    sii_message = fields.Text(
        string='SII Message',
        copy=False)
    sii_xml_request = fields.Text(
        string='SII XML Request',
        compute='set_values',
        store=True,
        copy=False)
    sii_xml_response = fields.Text(
        string='SII XML Response',
        copy=False)
    sii_send_ident = fields.Text(
        string='SII Send Identification',
        copy=False)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('NoEnviado', 'No Enviado'),
        ('Enviado', 'Enviado'),
        ('Aceptado', 'Aceptado'),
        ('Rechazado', 'Rechazado'),
        ('Reparo', 'Reparo'),
        ('Proceso', 'Proceso'),
        ('Reenviar', 'Reenviar'),
        ('Anulado', 'Anulado')],
        'Resultado'
        , index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=""" * The 'Draft' status is used when a user is encoding a new and\
unconfirmed Invoice.\n
* The 'Pro-forma' status is used the invoice does not have an invoice number.
* The 'Open' status is used when user create invoice, an invoice number is \
generated. Its in open status till user does not pay invoice.\n
* The 'Paid' status is set automatically when the invoice is paid. Its related
 journal entries may or may not be reconciled.\n
* The 'Cancelled' status is used when user cancel invoice.""")
    move_ids = fields.Many2many('account.move',
        readonly=True,
        states={'draft': [('readonly', False)]})

    invoice_ids = fields.Many2many(
        'account.invoice', readonly=True,
        states={'draft': [('readonly', False)]})

    tipo_libro = fields.Selection([
                ('ESPECIAL', 'Especial'),
                ('MENSUAL', 'Mensual'),
                ('RECTIFICA', 'Rectifica'),
                ],
                string="Tipo de Libro",
                default='MENSUAL',
                required=True,
                readonly=True,
                states={'draft': [('readonly', False)]}
            )
    tipo_operacion = fields.Selection([
                ('COMPRA', 'Compras'),
                ('VENTA', 'Ventas'),
                ('BOLETA', 'Boleta'),
                ],
                string="Tipo de operación",
                default="COMPRA",
                required=True,
                readonly=True,
                states={'draft': [('readonly', False)]}
            )
    tipo_envio = fields.Selection([
                ('AJUSTE', 'Ajuste'),
                ('TOTAL', 'Total'),
                ('PARCIAL', 'Parcial'),
                ('TOTAL', 'Total'),
                ],
                string="Tipo de Envío",
                default="TOTAL",
                required=True,
                readonly=True,
                states={'draft': [('readonly', False)]}
            )
    folio_notificacion = fields.Char(
        string="Folio de Notificación",
        readonly=True,
        states={'draft': [('readonly', False)]})
    impuestos = fields.One2many('account.move.book.tax',
        'book_id',
        string="Detalle Impuestos")
    currency_id = fields.Many2one('res.currency',
        string='Moneda',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility='always')
    total_afecto = fields.Monetary(
        string="Total Afecto",
        readonly=True,
        compute="set_values",
        store=True,)
    total_exento = fields.Monetary(
        string="Total Exento",
        readonly=True,
        compute='set_values',
        store=True,)
    total_iva = fields.Monetary(
        string="Total IVA",
        readonly=True,
        compute='set_values',
        store=True,)
    total_otros_imps = fields.Monetary(
        string="Total Otros Impuestos",
        readonly=True,
        compute='set_values',
        store=True,)
    total = fields.Monetary(
        string="Total Otros Impuestos",
        readonly=True,
        compute='set_values',
        store=True,)
    periodo_tributario = fields.Char(
        string='Periodo Tributario',
        required=True,
        readonly=True,
        default=lambda x: datetime.now().strftime('%Y-%m'),
        states={'draft': [('readonly', False)]})
    company_id = fields.Many2one(
        'res.company',
        string="Compañía",
        required=True,
        default=lambda self: self.env.user.company_id.id,
        readonly=True,
        states={'draft': [('readonly', False)]})
    name = fields.Char(
        string="Detalle",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]})
    fact_prop = fields.Float(
        string="Factor proporcionalidad",
        readonly=True,
        states={'draft': [('readonly', False)]})
    nro_segmento = fields.Integer(
        string="Número de Segmento",
        readonly=True,
        states={'draft': [('readonly', False)]})
    date = fields.Date(
        string="Fecha",
        required=True,
        readonly=True,
        default=lambda x: datetime.now(),
        states={'draft': [('readonly', False)]})
    boletas = fields.One2many('account.move.book.boletas',
        'book_id',
        string="Boletas",
        readonly=True,
        states={'draft': [('readonly', False)]})
    codigo_rectificacion = fields.Char(string="Código de Rectificación")

    @db_handler
    def _summary_by_period(self):
        return """
        select
        sii_code as "TpoDoc",
        totdoc as "TotDoc",
        f*total_exento as "TotMntExe",
        f*total_afecto - f*total_exento as "TotMntNeto",
        f*total_iva as "TotMntIVA",
        f*total as "TotMntTotal"
        from
        (select
        count(*) as totdoc,
        dc.sii_code,
        (case
        when dc.sii_code = 61 then -1
        else 1
        end) as f,
        cast(sum(mnt_exe) as integer) as "total_exento",
        cast(sum(amount_untaxed) as integer) as "total_afecto",
        cast((sum(amount_total)-sum(amount_untaxed)) as integer) as total_iva,
        cast(sum(amount_total) as integer) as total
        from account_invoice ai
        join sii_document_class dc
        on ai.sii_document_class_id = dc.id
        where ai.id in (%s) group by dc.sii_code) as a
        """

    @db_handler
    def _detail_by_period(self):
        return """
        select
        dc.sii_code as "TpoDoc",
        ai.sii_document_number as "NroDoc",
        ai.date_invoice as "FchDoc",
        trim(leading '0' from substring(rp.vat from 3 for 8)) || '-' ||
        right(rp.vat, 1) as "RUTDoc",
        rp.name as "RznSoc",
        ref.sii_code as "TpoDocRef",
        ref.origen as "FolioDocRef",
        cast(ai.mnt_exe as integer) as "MntExe",
        cast(ai.amount_untaxed as integer) - cast(ai.mnt_exe as integer) as "MntNeto",
        cast(ai.amount_total as integer) as "MntTotal"
        from account_invoice ai
        join sii_document_class dc
        on ai.sii_document_class_id = dc.id
        left join
        (select ar.invoice_id, ar.origen, dcl.sii_code from
        (select
        invoice_id,
        origen,
        "sii_referencia_TpoDocRef" as tipo
        from account_invoice_referencias) ar
        left join sii_document_class dcl
        on ar.tipo = dcl.id) as ref
        on ref.invoice_id = ai.id
        join res_partner rp
        on rp.id = ai.partner_id
        where ai.id in (%s)
        order by ai.id
        """

    def get_digital_signature_pem(self, comp_id):
        obj = user = False
        if 'responsable_envio' in self and self._ids:
            obj = user = self[0].responsable_envio
        if not obj:
            obj = user = self.env.user
        if not obj.cert:
            obj = self.env['res.users'].search(
                [("authorized_users_ids","=", user.id)])
            if not obj or not obj.cert:
                obj = self.env['res.company'].browse([comp_id.id])
                if not obj.cert or not user.id in obj.authorized_users_ids.ids:
                    return False
        signature_data = {
            'subject_name': obj.name,  # or obj.partner_id.name
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert,
            'rut_envia': obj.subject_serial_number, }
        return signature_data

    def _record_totals(self, jvalue):
        _logger.info('grabando totales en sii_xml_request #####-----####')
        _logger.info(json.dumps(jvalue))
        self.total_afecto = sum([x['TotMntNeto'] for x in jvalue])
        self.total_exento = sum([x['TotMntExe'] for x in jvalue])
        self.total_iva = sum([x['TotMntIVA'] for x in jvalue])
        self.total_otros_imps = 0
        self.total = sum([x['TotMntIVA'] for x in jvalue])

    @staticmethod
    def _envelope_book(xml_pret):
        return """<?xml version="1.0" encoding="ISO-8859-1"?>
<LibroCompraVenta xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte LibroCV_v10.xsd" version="1.0">\
{}</LibroCompraVenta>""".format(xml_pret)

    def _record_detail(self, dict1, dict2):
        dicttoxml.set_debug(False)
        inv_obj = self.env['account.invoice']
        resol_data = inv_obj.get_resolution_data(self.company_id)
        signature_d = self.get_digital_signature_pem(self.company_id)
        xml_detail1 = dicttoxml.dicttoxml(
            dict1, root=False, attr_type=False).replace(
            'item', 'TotalesPeriodo')
        xml_detail2 = dicttoxml.dicttoxml(
            dict2, root=False, attr_type=False).replace(
            'item', 'Detalle').replace('<Detalles>', '').replace(
            '</Detalles>', '')
        xml_detail2 = xml_detail2.replace(
            '<TpoDocRef/>', '').replace('<FolioDocRef/>', '').replace(
            '<TpoDocRef></TpoDocRef>', '').replace(
            '<FolioDocRef></FolioDocRef>', '')
        xml_envio_libro = """<EnvioLibro ID="{}">\
<Caratula>\
<RutEmisorLibro>{}</RutEmisorLibro>\
<RutEnvia>{}</RutEnvia>\
<PeriodoTributario>{}</PeriodoTributario>\
<FchResol>{}</FchResol>\
<NroResol>{}</NroResol>\
<TipoOperacion>{}</TipoOperacion>\
<TipoLibro>ESPECIAL</TipoLibro>\
<TipoEnvio>{}</TipoEnvio>\
<FolioNotificacion>{}</FolioNotificacion>\
</Caratula>{}{}<TmstFirma>{}</TmstFirma></EnvioLibro>""".format(
            self.name.replace(' ', '_'),
            inv_obj.format_vat(self.company_id.vat),
            signature_d['subject_serial_number'],
            self.periodo_tributario,
            resol_data['dte_resolution_date'],
            resol_data['dte_resolution_number'],
            self.tipo_operacion,
            self.tipo_envio,
            self.folio_notificacion,
            xml_detail1, xml_detail2,
            inv_obj.time_stamp(),
        )
        _logger.info(xml_envio_libro)
        xml1 = xml.dom.minidom.parseString(xml_envio_libro)
        xml_pret = xml1.toprettyxml()
        xml_pret = inv_obj.convert_encoding(xml_pret).replace(
            '<?xml version="1.0" ?>', '')
        # xml_pret = inv_obj.sign_seed(
        #     xml_pret, signature_d['priv_key'], signature_d['cert'])
        # _logger.info('esto es lo que se firma......')
        certp = signature_d['cert'].replace(
            BC, '').replace(EC, '').replace('\n', '')
        xml_pret = self._envelope_book(xml_pret)
        _logger.info(xml_pret)
        xml_pret = inv_obj.sign_full_xml(
            xml_pret, signature_d['priv_key'], certp,
            self.name.replace(' ', '_'), type='book')
        _logger.info(xml_pret)
        return xml_pret

    @api.depends('invoice_ids')
    def set_values(self):
        dict0 = self._summary_by_period()
        self._record_totals(dict0)
        dict1 = {'ResumenPeriodo': dict0}
        dict2 = {'Detalles': self._detail_by_period()}
        xml_pret = self._record_detail(dict1, dict2)
        self.sii_xml_request = xml_pret

    @api.multi
    def validar_libro(self):
        if not self.state or \
                self.state not in ['Borrador', 'NoEnviado', 'Rechazado']:
            raise UserError("El Libro  ya ha sido enviado")
        company_id = self.company_id
        doc_id = self.tipo_operacion + '_' + self.periodo_tributario
        result = self.send_xml_file(envio_dte, doc_id + '.xml', company_id)
        self.write({
            'sii_xml_response': result['sii_xml_response'],
            'sii_send_ident': result['sii_send_ident'],
            'state': result['sii_result'],
            'sii_xml_request': envio_dte
        })


class Boletas(models.Model):
    _name = 'account.move.book.boletas'

    currency_id = fields.Many2one('res.currency',
        string='Moneda',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility='always')
    tipo_boleta = fields.Many2one('sii.document_class',
        string="Tipo de Boleta",
        required=True,
        domain=[('document_letter_id.name','in',['B','M'])])
    rango_inicial = fields.Integer(
        string="Rango Inicial",
        required=True)
    rango_final = fields.Integer(
        string="Rango Final",
        required=True)
    cantidad_boletas = fields.Integer(
        string="Cantidad Boletas",
        rqquired=True)
    neto = fields.Monetary(
        string="Monto Neto",
        required=True)
    impuesto = fields.Many2one('account.tax',
        string="Impuesto",
        required=True,
        domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                ('active', '=', True)])
    monto_impuesto = fields.Monetary(
        compute='_monto_total',
        string="Monto Impuesto",
        required=True)
    monto_total = fields.Monetary(
        compute='_monto_total',
        string="Monto Total",
        required=True)
    book_id = fields.Many2one('account.move.book')

class ImpuestosLibro(models.Model):
    _name="account.move.book.tax"

    def get_monto(self):
        for t in self:
            t.amount = t.debit - t.credit
            if t.book_id.tipo_operacion in ['VENTA']:
                t.amount = t.credit - t.debit

    tax_id = fields.Many2one('account.tax', string="Impuesto")
    credit = fields.Monetary(string="Créditos", default=0.00)
    debit = fields.Monetary(string="Débitos", default=0.00)
    amount = fields.Monetary(
        compute="get_monto",
        string="Monto")
    currency_id = fields.Many2one('res.currency',
        string='Moneda',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility='always')
    book_id = fields.Many2one('account.move.book', string="Libro")
