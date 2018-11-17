# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import datetime as dtm
import calendar
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
tag_replace01 = pysiidte.tag_replace01
tag_replace_1 = pysiidte.tag_replace_1
tag_replace02 = pysiidte.tag_replace02
tag_replace_2 = pysiidte.tag_replace_2
tag_round = pysiidte.tag_replace_2
all_tags = tag_round + tag_replace01 + tag_replace_1 + tag_replace02 + \
           tag_replace_2


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

    @staticmethod
    def add_months(sourcedate, months):
        month = sourcedate.month - 1 + months
        year = sourcedate.year + month // 12
        month = month % 12 + 1
        day = min(sourcedate.day, calendar.monthrange(year, month)[1])
        return dtm.date(year, month, day)

    @staticmethod
    def first_period_day(period):
        return period + '-01'

    def first_next_period_day(self, period):
        strdate = self.first_period_day(period)
        date = dtm.datetime.strptime(strdate, '%Y-%m-%d')
        strdate = self.add_months(date, 1)
        return strdate

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
        'Resultado', readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=""" * The 'Draft' status is used when a user is encoding a new and\
unconfirmed Invoice.\n
* The 'Pro-forma' status is used the invoice does not have an invoice number.
* The 'Open' status is used when user create invoice, an invoice number is \
generated. Its in open status till user does not pay invoice.\n
* The 'Paid' status is set automatically when the invoice is paid. Its related
 journal entries may or may not be reconciled.\n
* The 'Cancelled' status is used when user cancel invoice.""")
    journal_ids = fields.Many2many(
        'account.journal', readonly=True, string='Journals',
        states={'draft': [('readonly', False)], })
    move_ids = fields.Many2many(
        'account.move', readonly=True, string="Account Moves",
        states={'draft': [('readonly', False)]})
    invoice_ids = fields.Many2many(
        'account.invoice', readonly=True, string="Invoices",
        states={'draft': [('readonly', False)]})

    report_type = fields.Selection([
                ('special', 'Especial'),
                ('monthly', 'Mensual'),
                ('amendment', 'Rectifica'), ], string="Book Type",
                default='monthly', required=True, readonly=True,
                states={'draft': [('readonly', False)]},
                help=u"""Mensual: corresponde a libros regulares.
Especial: corresponde a un libro solicitado vía una notificación.
Rectifica: Corresponde a un libro que reemplaza a uno ya recibido por el SII, \
requiere un Código de Autorización de Reemplazo de Libro Electrónico.""")
    operation_type = fields.Selection([
                ('purchase', 'Purchases'),
                ('sale', 'Sales'), ],
                string="Tipo de operación",
                default="purchase",
                required=True,
                readonly=True,
                states={'draft': [('readonly', False)]}
            )
    include_receipts = fields.Boolean('Include Receipts', default=True)
    sending_type = fields.Selection([
        ('adjustment', 'Ajuste'), ('partial', 'Parcial'), ('total', 'Total'), ],
        string="Tipo de Envío",
        default="total", required=True, readonly=True,
        states={'draft': [('readonly', False)], })
    notification_number = fields.Char(
        string="Notification invoice number", readonly=True,
        states={'draft': [('readonly', False)], })
    taxes = fields.One2many(
        'account.move.book.tax', 'book_id', string="Tax Detail")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True, track_visibility='always')
    total_vat_affected = fields.Monetary(
        string="Total VAT Affected", readonly=True, compute="set_values",
        store=True)
    total_exempt = fields.Monetary(
        string="Total Exempt", readonly=True, compute='set_values', store=True)
    total_vat = fields.Monetary(
        string="Total VAT", readonly=True, compute='set_values',
        store=True)
    total_other_taxes = fields.Monetary(
        string="Total Other Taxes", readonly=True, compute='set_values',
        store=True)
    total = fields.Monetary(
        string="Total", readonly=True, compute='set_values',
        store=True)
    fiscal_period = fields.Char(
        string='Fiscal Period', required=True, readonly=True,
        default=lambda x: datetime.now().strftime('%Y-%m'),
        states={'draft': [('readonly', False)], })
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.user.company_id.id, readonly=True,
        states={'draft': [('readonly', False)], })
    name = fields.Char(
        string="Detail", required=True, readonly=True,
        states={'draft': [('readonly', False)], })
    proportion_factor = fields.Float(
        string="Proportion Factor", readonly=True,
        states={'draft': [('readonly', False)], })
    nro_segmento = fields.Integer(
        string="Número de Segmento", readonly=True,
        states={'draft': [('readonly', False)], },
        help=u"""Sólo si el TIPO DE ENVIO es partial.""")
    date = fields.Date(
        string="Date", required=True, readonly=True,
        default=lambda x: datetime.now(),
        states={'draft': [('readonly', False)], })
    receipts = fields.One2many(
        'account.move.book.receipts', 'book_id', string="receipts",
        readonly=True, states={'draft': [('readonly', False)]})
    amendment_code = fields.Char(string="Código de Rectificación")

    @staticmethod
    def line_tax_view():
        a = """
select 	invoice_id,
journal_id,
line_id,
/*company_id,*/
tax_amount,
price_subtotal,
tax_code,
no_rec_code,
iva_uso_comun,
no_rec,
amount_total,
"TpoDoc",
"NroDoc",
"TpoImp",
"TasaImp",
"FchDoc",
"RUTDoc",
"RznSoc",
"TpoDocRef",
"FolioDocRef",
(CASE
WHEN tax_amount is not null THEN 0
ELSE price_subtotal
END) as "MntExe",
(CASE
WHEN tax_amount is null THEN 0
ELSE price_subtotal
END) as "MntNeto",
coalesce(round(
(CASE WHEN tax_code = 15 then 0
ELSE tax_amount END)
- (case when a.no_rec_code != '0' then
tax_amount else
(case when a.no_rec = '1' then tax_amount
else 0 end)
end) -
(case when iva_uso_comun then tax_amount
else 0 end), 2), 0.0) as "MntIVA",
(CASE
WHEN a.tax_code != 14 then 1
ELSE 0
END) as "OtrosImp",
(CASE
WHEN a.tax_code != 14 then a.tax_code
ELSE 0 END) as "CodImp",
(CASE
WHEN a.tax_code != 14 then "TasaImp"
ELSE 0 END) as "aTasaImp",
round((CASE
WHEN a.tax_code = 15 THEN tax_amount
ELSE 0
END), 0) as "MntImp",
round((CASE
WHEN "TasaImp" = 19 AND a.tax_code = 15
THEN tax_amount ELSE 0 END), 2)
as "IVARetTotal",
(CASE
WHEN "TasaImp" < 19 AND a.tax_code = 15
THEN tax_amount ELSE 0 END)
as "IVARetParcial",
(case
when a.no_rec_code != '0'
then 1
else (case
when a.no_rec = '1' then 1 else 0
end)
end) as "IVANoRec",
(case when a.no_rec_code != '0' then
cast(a.no_rec_code as integer) else
(case when a.no_rec = '1' then 1
else 0 end)
end) as "CodIVANoRec",
round((case when a.no_rec_code != '0' then
tax_amount
else
(case when a.no_rec = '1' then tax_amount
else 0 end)
end), 2) as "MntIVANoRec",
round((case when iva_uso_comun then
tax_amount
else 0 end), 2) as "IVAUsoComun",
(case when a.no_rec then 0 else 0 end)
as "MntSinCred",
round(a.amount_total, 0) as "MntTotal",
(case when a.no_rec then 0 else 0 end)
as "IVANoRetenido"
from
(select
ai.id as invoice_id,
aj.id as journal_id,
/*ai.company_id,*/
al.id as line_id,
dcl.sii_code as "TpoDoc",
cast(ai.sii_document_number as integer) as "NroDoc",
(CASE WHEN at.sii_code in (14, 15) THEN 1 ELSE 0 END) as "TpoImp",
COALESCE(round(abs(at.amount), 0), 0) as "TasaImp",
ai.date_invoice as "FchDoc",
trim(leading '0' from substring(rp.vat from 3 for 8)) || '-' ||
right(rp.vat, 1) as "RUTDoc",
left(rp.name, 50) as "RznSoc",
ref.sii_code as "TpoDocRef",
ref.origen as "FolioDocRef",
at.tax_group_id,
at.no_rec,
at.sii_code as tax_code,
ai.iva_uso_comun,
ai.no_rec_code,
al.price_subtotal,
abs(al.price_subtotal * at.amount / 100) as tax_amount,
ai.amount_untaxed,
ai.amount_total
from account_invoice_line_tax alt
join account_tax at
on alt.tax_id = at.id
right join account_invoice_line al
on al.id = alt.invoice_line_id
left join account_invoice ai
on ai.id = al.invoice_id
left join account_journal aj
on aj.id = ai.journal_id
left join sii_document_class dcl
on dcl.id = ai.sii_document_class_id
left join res_partner rp
on rp.id = ai.partner_id
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
order by ai.id, al.id, dcl.sii_code, at.id) a
"""
        # raise UserError(a)
        return a

    @db_handler
    def _get_invoices_from_selected_journals(self):
        period = self.fiscal_period
        _logger.info(period)
        journal_ids = [str(x.id) for x in self.journal_ids]
        journals = ', '.join(journal_ids)
        _logger.info(journals)
        first_day = self.first_period_day(period)
        _logger.info(first_day)
        last_day = self.first_next_period_day(period)
        _logger.info(last_day)
        a = """select 
ai.id
from account_invoice ai join account_move am
on ai.move_id = am.id
where ai.journal_id in (%s) and ai.state in ('open', 'paid') 
and am.state = 'posted'
and am.date >= '%s' and am.date < '%s'
""" % (str(journals), str(first_day), str(last_day))
        _logger.info(str(a))
        return a

    @db_handler
    def _summary_by_period(self):
        # better explicit than implicit ....
        if len(self.invoice_ids) == 0 and len(self.journal_ids) == 0:
            # first stage.. there are neither invoices nor journals
            return False
        elif len(self.invoice_ids) == 0 and len(self.journal_ids) != 0:
            # second stage .. journal is selected but invoices not found yet
            invoice_journal_ids = self._get_invoices_from_selected_journals()
            if len(invoice_journal_ids) == 0:
                # there are not invoices in journal. There is no possible
                # sale or purchase report in this situation
                raise UserError('No invoices found in selected journals')
            else:
                # some kind of invoice has been found (can't be??)
                account_invoice_ids = [
                    str(x['id']) for x in invoice_journal_ids]
                _logger.info(account_invoice_ids)
                # Inject invoice_ids in model
                values = [(6, 0, [x['id'] for x in invoice_journal_ids])]
                self.write({
                    'invoice_ids': values
                })
        elif len(self.invoice_ids) != 0 and len(self.journal_ids) == 0:
            # there is a selection of invoices without journal (can't be)
            raise UserError('No journal found for selected invoices')
        elif len(self.invoice_ids) != 0 and len(self.journal_ids) != 0:
            # there is a previous selection of invoices an journals.
            # may be a second time of entering a draft ledger, and need to
            # make calculations.
            raise UserError('previous selection')
        a = """
select
"TpoDoc"
"TpoDoc",
max("TpoImp") as "TpoImp",
count("TpoDoc") as "TotDoc",
sum(case when "MntExe" > 0 then 1 else 0 end) as "TotOpExe",
sum(cast("MntExe" as integer)) as "TotMntExe",
sum(cast("MntNeto" as integer)) as "TotMntNeto",
sum(case when "IVANoRec" > 0 then 0 else
(case when "MntIVA" = 0 then 0 else
(case when "TpoDoc" = 46 then Null else 1 end)
end)
end) as "TotOpIVARec",
sum(cast("MntIVA" as integer)) as "TotMntIVA",
/* tot otros imp */
sum(case when "MntImp" > 0 then 1 else 0 end) as "TotOtrosImp",
sum(case when "MntImp" > 0 then 15 else 0 end) as "CodImp",
sum(case when "MntImp" > 0 then "MntImp" else 0 end) as "TotMntImp",
/*sum(case when "IVARetTotal" > 0 then 1 else 0 end)
as "TotOpIVARetTotal",*/
sum(case when "IVARetTotal" > 0 then "IVARetTotal" else 0 end)
as "TotIVARetTotal",
/*sum(case when "IVARetParcial" > 0 then 1 else 0 end)
as "TotOpIVARetParcial",*/
sum(case when "IVARetParcial" > 0 then "IVARetParcial" else 0 end)
as "TotIVARetParcial",
/* TotOpActivoFijo, TotMntActivoFijo, TotMntIVAActivoFijo */
sum("IVANoRec") as "TotIVANoRec",
/* El TOT da la quantity de iteraciones dentro de
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
from(
select "TpoDoc",
"NroDoc",
max("TpoImp") as "TpoImp",
max("TasaImp") as "TasaImp",
"FchDoc",
"RUTDoc",
"RznSoc",
"TpoDocRef",
"FolioDocRef",
round(sum("MntExe"), 0) as "MntExe",
round(
(CASE WHEN "TpoDoc" = 46 THEN max("MntNeto")
ELSE sum("MntNeto") END), 0)
as "MntNeto",
round(sum("MntIVA"), 0) as "MntIVA",
max("OtrosImp") as "OtrosImp",
max("CodImp") as "CodImp",
max("aTasaImp") as "TasaImp",
max("MntImp") as "MntImp",
round(sum("IVARetTotal"), 0) as "IVARetTotal",
sum("IVARetParcial") as "IVARetParcial",
max("IVANoRec") as "IVANoRec",
max("CodIVANoRec") as "CodIVANoRec",
sum("MntIVANoRec") as "MntIVANoRec",
round(sum("IVAUsoComun"), 0) as "IVAUsoComun",
sum("MntSinCred") as "MntSinCred",
max("MntTotal") as "MntTotal",
max("IVANoRetenido") as "IVANoRetenido"
from (%s
where invoice_id in (%s)
) a
group by "TpoDoc", "NroDoc",
"FchDoc", "RUTDoc", "RznSoc",
"TpoDocRef", "FolioDocRef"
order by "TpoDoc", "NroDoc") b
group by
"TpoDoc"
""" % (self.proportion_factor, self.line_tax_view(), ', '.join(
            account_invoice_ids))
        # raise UserError(a)
        return a

    @db_handler
    def _detail_by_period(self):
        if True:  # try:
            account_invoice_ids = [str(x.id) for x in self.invoice_ids]
            # raise UserError('jfjfjfjf %s' % account_invoice_ids)
        else:  # except:
            return False
        a = """
select "TpoDoc",
"NroDoc",
max("TpoImp") as "TpoImp",
max("TasaImp") as "uTasaImp",
"FchDoc",
"RUTDoc",
"RznSoc",
"TpoDocRef",
"FolioDocRef",
round(sum("MntExe"), 0) as "MntExe",
round(
(CASE WHEN "TpoDoc" = 46 THEN max("MntNeto")
ELSE sum("MntNeto") END), 0)
as "MntNeto",
round(sum("MntIVA"), 0) as "MntIVA",
max("OtrosImp") as "OtrosImp",
max("CodImp") as "CodImp",
max("aTasaImp") as "TasaImp",
max("MntImp") as "MntImp",
round(sum("IVARetTotal"), 0) as "IVARetTotal",
sum("IVARetParcial") as "IVARetParcial",
max("IVANoRec") as "IVANoRec",
max("CodIVANoRec") as "CodIVANoRec",
round(sum("MntIVANoRec"), 0) as "MntIVANoRec",
round(sum("IVAUsoComun"), 0) as "IVAUsoComun",
sum("MntSinCred") as "MntSinCred",
max("MntTotal") as "MntTotal",
max("IVANoRetenido") as "IVANoRetenido"
from (%s
where invoice_id in (%s)
) a
group by "TpoDoc", "NroDoc",
"FchDoc", "RUTDoc", "RznSoc",
"TpoDocRef", "FolioDocRef"
order by "TpoDoc", "NroDoc"
        """ % (self.line_tax_view(), ', '.join(account_invoice_ids))
        # raise UserError(a)
        return a

    def _record_totals(self, jvalue):
        _logger.info(json.dumps(jvalue))
        if jvalue:
            self.total_vat_affected = sum([x['TotMntNeto'] for x in jvalue])
            self.total_exempt = sum([x['TotMntExe'] for x in jvalue])
            self.total_vat = sum([x['TotMntIVA'] for x in jvalue])
            self.total_other_taxes = 0
            self.total = sum([x['TotMntIVA'] for x in jvalue])

    @staticmethod
    def _envelope_book(xml_pret):
        return """<?xml version="1.0" encoding="ISO-8859-1"?>
<Libropurchasesale xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte LibroCV_v10.xsd" version="1.0">\
{}</Libropurchasesale>""".format(xml_pret)

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
                    print k, v
                elif k in son_tags and int(v) != 0:
                    try:
                        dict2nlist[parent_tag][k] = v
                    except KeyError:
                        pass
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
            dict1n = self.insert_son_values(
                dict1n, 'ResumenPeriodo', 'TotOtrosImp',
                ['CodImp', 'TotMntImp'])
            xml_detail1 = self.replace_tags(self.replace_tags(
                self.replace_tags(
                    dicttoxml.dicttoxml(
                        dict1n, root=False, attr_type=False).replace(
                            'item', 'TotalesPeriodo').replace(
                        '>0.0<', '>0<').replace(
                        '.0<', '<'), tag_replace01, '0'), tag_replace_1, ''),
                    tag_replace01, '0.0')
            dict2n = self.insert_son_values(
                dict2, 'Detalles', 'IVANoRec', ['CodIVANoRec', 'MntIVANoRec'])
            # raise UserError(json.dumps(dict2n))
            dict2n = self.insert_son_values(
                dict2n, 'Detalles', 'OtrosImp', ['CodImp', 'TasaImp', 'MntImp'])
            # print dict2n
            xml_detail2 = dicttoxml.dicttoxml(
                dict2n, root=False, attr_type=False).replace(
                'item', 'Detalle').replace('<Detalles>', '').replace(
                '</Detalles>', '').replace('>0.0<', '>0<').replace(
                    '.0<', '<')
            xml_detail2 = self.replace_tags(
                self.replace_tags(xml_detail2.replace(
                    '<TpoDocRef/>', '').replace(
                    '<FolioDocRef/>', ''), tag_replace02, '0'),
                tag_replace_2, '').replace('uTasaImp', 'TasaImp')
            print xml_detail2
            # raise UserError('xml_detail2')
            xml_envio_report = """<EnvioLibro ID="{}">\
<Caratula>\
<RutEmisorLibro>{}</RutEmisorLibro>\
<RutEnvia>{}</RutEnvia>\
<PeriodoTributario>{}</PeriodoTributario>\
<FchResol>{}</FchResol>\
<NroResol>{}</NroResol>\
<TipoOperacion>{}</TipoOperacion>\
<TipoLibro>{}</TipoLibro>\
<TipoEnvio>{}</TipoEnvio>\
<FolioNotificacion>{}</FolioNotificacion>\
<CodAutRec>{}</CodAutRec>\
</Caratula>{}{}<TmstFirma>{}</TmstFirma></EnvioLibro>""".format(
                self.name.replace(' ', '_'),
                inv_obj.format_vat(self.company_id.vat),
                signature_d['subject_serial_number'],
                self.fiscal_period,
                resol_data['dte_resolution_date'],
                resol_data['dte_resolution_number'],
                self.operation_type,
                self.report_type,
                self.sending_type,
                self.notification_number or '',
                self.amendment_code or '',
                xml_detail1, xml_detail2, inv_obj.time_stamp()).replace(
                '<FolioNotificacion></FolioNotificacion>', '', 1).replace(
                '<CodAutRec></CodAutRec>', '', 1)
            _logger.info(xml_envio_report)
            xml1 = xml.dom.minidom.parseString(xml_envio_report)
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
            _logger.info('Could not get files (first attempt)')
            return False

    @api.depends('name', 'date', 'company_id', 'invoice_ids', 'fiscal_period',
                 'operation_type', 'report_type', 'sending_type',
                 'proportion_factor')
    def set_values(self):
        if not self.name and not self.invoice_ids:
            return
        dict0 = self._summary_by_period()
        self._record_totals(dict0)
        dict1 = {'ResumenPeriodo': dict0}
        dict2 = {'Detalles': self._detail_by_period()}
        xml_pret = self._record_detail(dict1, dict2)
        self.sii_xml_request = xml_pret

    @api.multi
    def validate_report(self):
        inv_obj = self.env['account.invoice']
        if self.state not in ['draft', 'NoEnviado', 'Rechazado']:
            raise UserError('El libro se encuentra en estado: {}'.format(
                self.state))
        company_id = self.company_id
        doc_id = self.operation_type + '_' + self.fiscal_period
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
            raise UserError('Connection error')
        xml_response = xmltodict.parse(self.sii_xml_response)
        _logger.info(xml_response)
        if self.state == 'Enviado':
            status = self._get_send_status(
                self.sii_send_ident, signature_d, token)
            if self.state != 'Proceso':
                return status


class Receipts(models.Model):
    _name = 'account.move.book.receipts'

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True, track_visibility='always')
    receipt_type = fields.Many2one(
        'sii.document_class', string="Receipt Type",
        required=True, domain=[('document_letter_id.name', 'in', ['B', 'M'])])
    initial_range = fields.Integer(
        string="Initial Range", required=True)
    final_range = fields.Integer(
        string="Final Range", required=True)
    quantity_receipts = fields.Integer(
        string="Cantidad receipts", required=True)
    net_amount = fields.Monetary(string="Net Amount", required=True)
    tax = fields.Many2one(
        'account.tax', string="Tax", required=True,
        domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                ('active', '=', True)])
    amount_tax = fields.Monetary(
        compute='_amount_total', string="Tax Amount", required=True)
    amount_total = fields.Monetary(
        compute='_amount_total', string="Total Amount", required=True)
    book_id = fields.Many2one('account.move.book')


class BookTaxes(models.Model):
    _name = "account.move.book.tax"

    def get_monto(self):
        for t in self:
            t.amount = t.debit - t.credit
            if t.book_id.operation_type in ['sale']:
                t.amount = t.credit - t.debit

    tax_id = fields.Many2one('account.tax', string="Tax")
    credit = fields.Monetary(string="Créditos", default=0.00)
    debit = fields.Monetary(string="Débitos", default=0.00)
    amount = fields.Monetary(compute="get_monto", string="Amount")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True, track_visibility='always')
    book_id = fields.Many2one('account.move.book', string="Book")
