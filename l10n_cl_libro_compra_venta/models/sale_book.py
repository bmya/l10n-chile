# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import json
import collections
import pysiidte
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
from bs4 import BeautifulSoup as bs

server_url = pysiidte.server_url
BC = pysiidte.BC
EC = pysiidte.EC
connection_status = pysiidte.connection_status


def to_json(colnames, rows):
    all_data = []
    for row in rows:
        each_row = collections.OrderedDict()
        i = 0
        for colname in colnames:
            each_row[colname] = pysiidte.char_replace(row[i])
            i += 1
        all_data.append(each_row)
    return all_data


def db_handler(method):
    def call(self, *args, **kwargs):
        _logger.info(args)
        query = method(self, *args, **kwargs)
        cursor = self.env.cr
        try:
            cursor.execute(query)
        except:
            return False
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
                states={'draft': [('readonly', False)]},
                help=u"""Mensual: corresponde a libros regulares.
Especial: corresponde a un libro solicitado vía una notificación.
Rectifica: Corresponde a un libro que reemplaza a uno ya recibido por el SII, \
requiere un Código de Autorización de Reemplazo de Libro Electrónico.""")
    tipo_operacion = fields.Selection([
                ('COMPRA', 'Compras'),
                ('VENTA', 'Ventas'),
                ('BOLETA', 'Boleta'), ],
                string="Tipo de operación",
                default="COMPRA",
                required=True,
                readonly=True,
                states={'draft': [('readonly', False)]}
            )
    tipo_envio = fields.Selection([
        ('AJUSTE', 'Ajuste'), ('TOTAL', 'Total'),
        ('PARCIAL', 'Parcial'), ('TOTAL', 'Total'), ], string="Tipo de Envío",
        default="TOTAL", required=True, readonly=True,
        states={'draft': [('readonly', False)], })
    folio_notificacion = fields.Char(
        string="Folio de Notificación", readonly=True,
        states={'draft': [('readonly', False)], })
    impuestos = fields.One2many(
        'account.move.book.tax', 'book_id', string="Detalle Impuestos")
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True, track_visibility='always')
    total_afecto = fields.Monetary(
        string="Total Afecto", readonly=True, compute="set_values",
        store=True)
    total_exento = fields.Monetary(
        string="Total Exento", readonly=True, compute='set_values', store=True)
    total_iva = fields.Monetary(
        string="Total IVA", readonly=True, compute='set_values',
        store=True)
    total_otros_imps = fields.Monetary(
        string="Total Otros Impuestos", readonly=True, compute='set_values',
        store=True)
    total = fields.Monetary(
        string="Total Otros Impuestos", readonly=True, compute='set_values',
        store=True)
    periodo_tributario = fields.Char(
        string='Periodo Tributario', required=True, readonly=True,
        default=lambda x: datetime.now().strftime('%Y-%m'),
        states={'draft': [('readonly', False)], })
    company_id = fields.Many2one(
        'res.company', string="Compañía", required=True,
        default=lambda self: self.env.user.company_id.id, readonly=True,
        states={'draft': [('readonly', False)], })
    name = fields.Char(
        string="Detalle", required=True, readonly=True,
        states={'draft': [('readonly', False)], })
    fact_prop = fields.Float(
        string="Factor proporcionalidad", readonly=True,
        states={'draft': [('readonly', False)], })
    nro_segmento = fields.Integer(
        string="Número de Segmento", readonly=True,
        states={'draft': [('readonly', False)], },
        help=u"""Sólo si el TIPO DE ENVIO es PARCIAL.""")
    date = fields.Date(
        string="Fecha", required=True, readonly=True,
        default=lambda x: datetime.now(),
        states={'draft': [('readonly', False)], })
    boletas = fields.One2many(
        'account.move.book.boletas', 'book_id', string="Boletas", readonly=True,
        states={'draft': [('readonly', False)]})
    codigo_rectificacion = fields.Char(string="Código de Rectificación")

    @db_handler
    def _summary_by_period(self):
        if True:  # try:
            account_invoice_ids = [str(x.id) for x in self.invoice_ids]
        else:  # except:
            return False
        return """
        select
        "TpoDoc",
        max("TpoImp") as "TpoImp",
        count("TpoImp") as "TotDoc",
        sum(case when "MntExe" > 0 then 1 else 0 end) as "TotOpExe",
        sum(cast("MntExe" as integer)) as "TotMntExe",
        sum(cast("MntNeto" as integer)) as "TotMntNeto",
        sum(case when "IVANoRec" > 0 then 0 else
        (case when "MntIVA" = 0 then 0 else
        (case when "TpoDoc" = 46 then Null else 1 end)
        end)
        end) as "TotOpIVARec",
        sum(cast("MntIVA" as integer)) as "TotMntIVA",
        sum(case when "IVARetTotal" > 0 then 1 else 0 end)
        as "TotOpIVARetTotal",
        sum(case when "IVARetTotal" > 0 then "IVARetTotal" else 0 end)
        as "TotIVARetTotal",
        sum(case when "IVARetParcial" > 0 then 1 else 0 end)
        as "TotOpIVARetParcial",
        sum(case when "IVARetParcial" > 0 then "IVARetParcial" else 0 end)
        as "TotIVARetParcial",
        /* TotOpActivoFijo, TotMntActivoFijo, TotMntIVAActivoFijo */
        sum("IVANoRec") as "TotIVANoRec",
        /* El TOT da la cantidad de iteraciones dentro de
        la matriz (normalmente 1)*/
        /*max((case when "IVANoRec" > 0 then at_sii_code else 0 end))
        as "CodIVANoRec",*/
        /* revisar repeticion y revisar de donde obtener el codigo */
        max((case when "IVANoRec" > 0 then
        "CodIVANoRec" else '0' end)) as "CodIVANoRec",
        sum((case when "IVANoRec" > 0 then 1 else 0 end)) as "TotOpIVANoRec",
        sum(cast(round((case when "IVANoRec" > 0 then "MntIVANoRec" else 0 end),
        0) as integer)) as "TotMntIVANoRec",
        sum(cast(round((case when "IVAUsoComun" > 0 then 1 else 0 end),
        0) as integer)) as "TotOpIVAUsoComun",
        sum(cast(round((case when "IVAUsoComun" > 0 then "IVAUsoComun" else
        0 end),
        0) as integer)) as "TotIVAUsoComun",
        sum(cast(round((case when "IVAUsoComun" > 0 then "IVAUsoComun"
        * %s else 0 end),
        0) as integer)) as "TotCredIVAUsoComun",
        sum(cast(round((case when "IVANoRec" > 0 then 0 else 0 end), 0)
        as integer)) as "TotImpSinCredito",
        sum(cast("MntExe" + "MntNeto" + "MntIVA" + "MntIVANoRec"
        + "IVAUsoComun"
        - (case when "IVARetTotal" > 0 then "IVARetTotal" else 0 end)
        - (case when "IVARetParcial" > 0 then "IVARetParcial" else 0 end)
        as integer)) as "TotMntTotal",
        sum(case when "IVANoRetenido" > 0 then 1 else 0 end)
        as "TotOpIVANoRetenido",
        sum(case when "IVANoRetenido" > 0 then "IVANoRetenido" else 0 end)
        as "TotIVANoRetenido"
        from
        (
        select
        /*line_id,*/
        max("TpoDoc") as "TpoDoc",
        max("NroDoc") as "NroDoc",
        max(1) as "TpoImp",
        max(round("TasaImp", 2)) as "TasaImp",
        max("FchDoc") as "FchDoc",
        /*CdgSIISucur*/
        max("RUTDoc") as "RUTDoc",
        max("RznSoc") as "RznSoc",
        max("TpoDocRef") as "TpoDocRef",
        max("FolioDocRef") as "FolioDocRef",
        sum(cast((CASE
        WHEN tax_amount is not null THEN 0
        ELSE price_subtotal
        END) as integer)) as "MntExe",
        /* es cast(sum aca y sum(cast en el resumen por redondeo */
        sum(cast((CASE
        WHEN tax_amount is null THEN 0
        ELSE price_subtotal
        END) as integer)) as "MntNeto",
        cast(sum((CASE
        WHEN tax_amount is null then 0
        ELSE tax_amount - "MntIVANoRec" - "IVAUsoComun"
        END)) as integer) as "MntIVA",
        cast(sum((CASE
        WHEN rcn = 19 THEN (rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) as "IVARetTotal",
        cast(sum((CASE
        WHEN rcn < 19 THEN (rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) as "IVARetParcial",
        cast(sum((CASE
        WHEN rcn < 19 AND at_sii_code = 15 THEN (1 - rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) as "IVANoRetenido",
        /* OJO RECALCULAR EN BASE A DIFERENCIA CON EL RESTO */
        /*MntActivoFijo*/
        /*MntIVAActivoFijo*/
        sum("IVANoRec") as "IVANoRec",
        max("CodIVANoRec") as "CodIVANoRec",
        sum("MntIVANoRec") as "MntIVANoRec",
        sum("IVAUsoComun") as "IVAUsoComun",
        /*"OtrosImp--",*/
        sum("MntSinCred") as "MntSinCred",
        max("MntTotal") -
        cast(sum((CASE
        WHEN rcn = 19 THEN (rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) -
        cast(sum((CASE
        WHEN rcn < 19 THEN (rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) as "MntTotal"
        /*max(at_sii_code) as at_sii_code,
        max(taxz_amount) as taxz_amount
        at_sii_code y taxz_amount van solo en resumen
        para calculo auxiliar*/
        /*IVANoRetenido*/
        /*TabPuros*/
        /*TabCigarrillos*/
        /*TabElaborado*/
        /*ImpVehiculo*/
        from
        (select
        dc.sii_code as "TpoDoc",
        al.invoice_id as invoice_id,
        cast(ai.sii_document_number as integer) as "NroDoc",
        at.amount as "TasaImp",
        ai.date_invoice as "FchDoc",
        trim(leading '0' from substring(rp.vat from 3 for 8)) || '-' ||
        right(rp.vat, 1) as "RUTDoc",
        left(rp.name, 50) as "RznSoc",
        ref.sii_code as "TpoDocRef",
        ref.origen as "FolioDocRef",
        al.id as line_id,
        al.price_subtotal,
        al.product_id,
        al.name as al_pname,
        at.name as at_name,
        at.tax_group_id,
        at.amount as taxz_amount,
        round(al.price_subtotal * at.amount / 100, 2) as tax_amount,
        /*MntActivoFijo*/
        /*MntIVAActivoFijo*/
        at.no_rec,
        at.retencion as rcn,
        at.sii_code as at_sii_code,
        at.amount,
        at.sii_code,
        at.type_tax_use,
        (case when ai.no_rec_code != '0' then 1 else 0 end) as "IVANoRec",
        (case when ai.no_rec_code != '0' then
        cast(ai.no_rec_code as integer) else 0 end) as "CodIVANoRec",
        cast(round((case when ai.no_rec_code != '0' then
        round(al.price_subtotal * at.amount / 100, 2)
        else 0 end), 0) as
        integer) as "MntIVANoRec",
        cast(round((case when ai.iva_uso_comun then
        round(al.price_subtotal * at.amount / 100, 2)
        else 0 end), 0) as integer) as "IVAUsoComun",
        cast(round((case when at.no_rec then 0 else 0 end), 0) as
        integer) as "MntSinCred",
        cast(ai.amount_total as integer) as "MntTotal"
        /*IVANoRetenido*/
        /*TabPuros*/
        /*TabCigarrillos*/
        /*TabElaborado*/
        /*ImpVehiculo*/
        from account_invoice ai
        left join account_invoice_line al
        on ai.id = al.invoice_id
        left join sii_document_class dc
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
        left join account_invoice_line_tax alt
        on al.id = alt.invoice_line_id
        left join account_tax at
        on alt.tax_id = at.id
        left join res_partner rp
        on rp.id = ai.partner_id
        where al.company_id = 1
        and al.invoice_id in (%s)
        order by "TpoDoc", "NroDoc"
        ) as a
        group by "TpoDoc", "NroDoc"
        /*group by line_id
        order by line_id*/) as b
        group by "TpoDoc"
        order by "TpoDoc"
        """ % (self.fact_prop, ', '.join(account_invoice_ids))

    @db_handler
    def _detail_by_period(self):
        if True:  # try:
            account_invoice_ids = [str(x.id) for x in self.invoice_ids]
        else:  # except:
            return False
        return """
        /*
        SUMA DE DETALLE DE MONTOS nueva!
        Esta no necesita que esté guardado el
        "mnt_exe" en la factura
        */
        select
        /*line_id,*/
        max("TpoDoc") as "TpoDoc",
        max("NroDoc") as "NroDoc",
        max(1) as "TpoImp",
        max(round("TasaImp", 2)) as "TasaImp",
        max("FchDoc") as "FchDoc",
        /*CdgSIISucur*/
        max("RUTDoc") as "RUTDoc",
        max("RznSoc") as "RznSoc",
        max("TpoDocRef") as "TpoDocRef",
        max("FolioDocRef") as "FolioDocRef",
        cast(sum(CASE
        WHEN tax_amount is not null THEN 0
        ELSE price_subtotal
        END) as integer) as "MntExe",
        /* es cast(sum aca y sum(cast en el resumen por redondeo */
        sum(cast((CASE
        WHEN tax_amount is null THEN 0
        ELSE price_subtotal
        END) as integer)) as "MntNeto",
        cast(sum((CASE
        WHEN tax_amount is null then 0
        ELSE tax_amount - "MntIVANoRec" - "IVAUsoComun"
        END)) as integer) as "MntIVA",
        cast(sum((CASE
        WHEN rcn = 19 THEN (rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) as "IVARetTotal",
        cast(sum((CASE
        WHEN rcn < 19 THEN (rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) as "IVARetParcial",
        /* OJO RECALCULAR EN BASE A DIFERENCIA CON EL RESTO */
        /*MntActivoFijo*/
        /*MntIVAActivoFijo*/
        sum("IVANoRec") as "IVANoRec",
        max("CodIVANoRec") as "CodIVANoRec",
        sum("MntIVANoRec") as "MntIVANoRec",
        sum("IVAUsoComun") as "IVAUsoComun",
        /*"OtrosImp--",*/
        sum("MntSinCred") as "MntSinCred",
        /*max(at_sii_code) as at_sii_code,
        max(taxz_amount) as taxz_amount
        at_sii_code y taxz_amount van solo en resumen
        para calculo auxiliar*/
        /*IVANoRetenido*/
        /*TabPuros*/
        /*TabCigarrillos*/
        /*TabElaborado*/
        /*ImpVehiculo*/
        max("MntTotal") -
        cast(sum((CASE
        WHEN rcn = 19 THEN (rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) -
        cast(sum((CASE
        WHEN rcn < 19 THEN (rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) as "MntTotal",
	cast(sum((CASE
        WHEN rcn < 19 AND at_sii_code = 15 THEN (1 - rcn / 19) * tax_amount
        ELSE 0
        END)) as integer) as "IVANoRetenido"
        from
        (select
        dc.sii_code as "TpoDoc",
        al.invoice_id as invoice_id,
        cast(ai.sii_document_number as integer) as "NroDoc",
        at.amount as "TasaImp",
        ai.date_invoice as "FchDoc",
        trim(leading '0' from substring(rp.vat from 3 for 8)) || '-' ||
        right(rp.vat, 1) as "RUTDoc",
        left(rp.name, 50) as "RznSoc",
        ref.sii_code as "TpoDocRef",
        ref.origen as "FolioDocRef",
        al.id as line_id,
        al.price_subtotal,
        al.product_id,
        al.name as al_pname,
        at.name as at_name,
        at.tax_group_id,
        at.amount,
        round(al.price_subtotal * at.amount / 100, 2) as tax_amount,
        /*MntActivoFijo*/
        /*MntIVAActivoFijo*/
        at.no_rec,
        at.retencion as rcn,
        at.sii_code as at_sii_code,
        at.amount,
        at.sii_code,
        at.type_tax_use,
        (case when ai.no_rec_code != '0' then 1 else 0 end) as "IVANoRec",
        (case when ai.no_rec_code != '0' then
        cast(ai.no_rec_code as integer) else 0 end) as "CodIVANoRec",
        cast(round((case when ai.no_rec_code != '0' then
        round(al.price_subtotal * at.amount / 100, 2)
        else 0 end), 0) as
        integer) as "MntIVANoRec",
        cast(round((case when ai.iva_uso_comun then
        round(al.price_subtotal * at.amount / 100, 2)
        else 0 end), 0) as integer) as "IVAUsoComun",
        cast(round((case when at.no_rec then 0 else 0 end), 0) as
        integer) as "MntSinCred",
        cast(ai.amount_total as integer) as "MntTotal"
        /*IVANoRetenido*/
        /*TabPuros*/
        /*TabCigarrillos*/
        /*TabElaborado*/
        /*ImpVehiculo*/
        from account_invoice ai
        left join account_invoice_line al
        on ai.id = al.invoice_id
        left join sii_document_class dc
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
        left join account_invoice_line_tax alt
        on al.id = alt.invoice_line_id
        left join account_tax at
        on alt.tax_id = at.id
        left join res_partner rp
        on rp.id = ai.partner_id
        where al.company_id = 1
        and al.invoice_id in (%s)
        order by "TpoDoc", "NroDoc"
        ) as a
        group by "TpoDoc", "NroDoc"
        /*group by line_id
        order by line_id*/
        """ % ', '.join(account_invoice_ids)

    def _record_totals(self, jvalue):
        _logger.info(json.dumps(jvalue))
        if jvalue:
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

    @staticmethod
    def insert_son_values(
            parent_dictionary, grand_parent_tag, parent_tag, son_tags):
        dict2n = collections.OrderedDict()
        dict2n[grand_parent_tag] = []
        for d2 in parent_dictionary[grand_parent_tag]:
            dict2nlist = collections.OrderedDict()
            for k, v in d2.iteritems():
                if k == parent_tag:
                    dict2nlist[k] = collections.OrderedDict()
                    print 'EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE'
                    print k, v
                elif k in son_tags and int(v) != 0:
                    dict2nlist[parent_tag][k] = v
                else:
                    dict2nlist[k] = v
                print k, v
            dict2n[grand_parent_tag].append(dict2nlist)
        return dict2n

    @staticmethod
    def replace_tags(xml_part, tag_list, zero):
        for tag in tag_list:
            xml_part = xml_part.replace('<{0}>{1}</{0}>'.format(tag, zero), '')
        return xml_part

    def _record_detail(self, dict1, dict2):
        tag_replace01 = ['TotOpExe', 'TotOpIVARec', 'CodIVANoRec',
                         'TotOpIVARetTotal', 'TotIVARetTotal',
                         'TotOpIVARetParcial', 'TotIVARetParcial',
                         'TotOpIVANoRetenido', 'TotIVANoRetenido',
                         'TotOpIVANoRec', 'TotMntIVANoRec',
                         'TotOpIVAUsoComun', 'TotCredIVAUsoComun',
                         'TotIVAUsoComun', 'TotImpSinCredito']
        tag_replace_1 = ['TpoImp', 'TotOpIVARec', 'TotIVANoRec']
        tag_replace02 = ['CodIVANoRec', 'MntIVANoRec', 'IVAUsoComun',
                         'MntSinCred', 'IVANoRetenido', 'IVARetTotal',
                         'IVARetParcial']
        tag_replace_2 = ['TpoDocRef', 'FolioDocRef', 'TpoImp', 'TasaImp',
             'IVANoRec']
        if True:
            dicttoxml.set_debug(False)
            inv_obj = self.env['account.invoice']
            try:
                resol_data = inv_obj.get_resolution_data(self.company_id)
                signature_d = inv_obj.get_digital_signature_pem(self.company_id)
            except:
                _logger.info(u'First entry: unknown company')
                return False
            dict1n = self.insert_son_values(
                dict1, 'ResumenPeriodo', 'TotIVANoRec',
                ['CodIVANoRec', 'TotMntIVANoRec', 'TotOpIVANoRec'])
            xml_detail1 = self.replace_tags(self.replace_tags(
                dicttoxml.dicttoxml(
                    dict1n, root=False, attr_type=False).replace(
                    'item', 'TotalesPeriodo'), tag_replace01, '0'),
                tag_replace_1, '')
            dict2n = self.insert_son_values(
                dict2, 'Detalles', 'IVANoRec', ['CodIVANoRec', 'MntIVANoRec'])
            # print dict2n
            xml_detail2 = dicttoxml.dicttoxml(
                dict2n, root=False, attr_type=False).replace(
                'item', 'Detalle').replace('<Detalles>', '').replace(
                '</Detalles>', '')
            xml_detail2 = self.replace_tags(
                self.replace_tags(xml_detail2.replace(
                    '<TpoDocRef/>', '').replace(
                    '<FolioDocRef/>', ''), tag_replace02, '0'),
                tag_replace_2, '')
            print xml_detail2
            # raise UserError('xml_detail2')
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
            if True:  # try:
                xml_pret = inv_obj.convert_encoding(
                    xml_pret, 'ISO-8859-1').replace(
                    '<?xml version="1.0" ?>', '')
            else:  # except:
                _logger.info(u'no pude decodificar algún caracter. La versión \
guardada del xml es la siguiente: {}'.format(xml_pret))
                # raise UserError('xml pret sin decodificar')
            certp = signature_d['cert'].replace(
                BC, '').replace(EC, '').replace('\n', '')
            xml_pret = self._envelope_book(xml_pret)
            _logger.info(xml_pret)
            xml_pret = inv_obj.sign_full_xml(
                xml_pret, signature_d['priv_key'], certp,
                self.name.replace(' ', '_'), type='book')
            _logger.info(xml_pret)
            return xml_pret
        else:  # except:
            _logger.info('no se pudo obtener archivos (primer pasada)')
            return False

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
        inv_obj = self.env['account.invoice']
        if self.state not in ['draft', 'NoEnviado', 'Rechazado']:
            raise UserError('El libro se encuentra en estado: {}'.format(
                self.state))
        company_id = self.company_id
        doc_id = self.tipo_operacion + '_' + self.periodo_tributario
        result = inv_obj.send_xml_file(
            self.sii_xml_request, doc_id + '.xml', company_id)
        self.write({
            'sii_xml_response': result['sii_xml_response'],
            'sii_send_ident': result['sii_send_ident'],
            'state': result['sii_result'],
            # 'sii_xml_request': envio_dte
        })

    def _get_send_status(self, track_id, signature_d, token):
        url = server_url[
                  self.company_id.dte_service_provider] + 'QueryEstUp.jws?WSDL'
        ns = 'urn:' + server_url[
            self.company_id.dte_service_provider] + 'QueryEstUp.jws'
        _server = SOAPProxy(url, ns)
        respuesta = _server.getEstUp(
            self.company_id.vat[2:-1], self.company_id.vat[-1], track_id, token)
        self.sii_receipt = respuesta
        resp = xmltodict.parse(respuesta)
        status = False
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "-11":
            status = {
                'warning': {
                    'title': _('Error -11'),
                    'message': _("Error -11: Espere a que sea aceptado por el \
SII, intente en 5s más")}}
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "EPR":
            self.state = "Proceso"
            if 'SII:RESP_BODY' in resp['SII:RESPUESTA'] and resp[
                'SII:RESPUESTA']['SII:RESP_BODY']['RECHAZADOS'] == "1":
                self.sii_result = "Rechazado"
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "RCT":
            self.state = "Rechazado"
            status = {
                'warning': {
                    'title': _('Error RCT'),
                    'message': _(resp['SII:RESPUESTA']['GLOSA'])}}
        return status


    @api.multi
    def ask_for_dte_status(self):
        inv_obj = self.env['account.invoice']
        if True:  # try:
            signature_d = inv_obj.get_digital_signature_pem(
                self.company_id)
            token = pysiidte.sii_token(
                self.company_id.dte_service_provider, signature_d['priv_key'],
                signature_d['cert'])
        else:  # except:
            raise UserError('Error de conexion')
        xml_response = xmltodict.parse(self.sii_xml_response)
        _logger.info(xml_response)
        if self.state == 'Enviado':
            status = self._get_send_status(
                self.sii_send_ident, signature_d, token)
            if self.state != 'Proceso':
                return status


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
