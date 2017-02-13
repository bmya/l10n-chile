# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import json
from lxml import etree
import pytz
import collections
import urllib3
import xmltodict
import dicttoxml
import base64
import cchardet
from SOAPpy import SOAPProxy
from signxml import *
from xml.dom.minidom import parseString
try:
    urllib3.disable_warnings()
except:
    pass
_logger = logging.getLogger(__name__)
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
from .commonmethods import LibreDte as ld
from .commonmethods import CommonMethods as cm
from .commonmethods import PySIIDTE as si

# timbre patrón. Permite parsear y formar el
# ordered-dict patrón corespondiente al documento

# Public vars definition
timbre = """<TED version="1.0"><DD><RE>99999999-9</RE><TD>11</TD><F>1</F>\
<FE>2000-01-01</FE><RR>99999999-9</RR><RSR>\
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</RSR><MNT>10000</MNT><IT1>IIIIIII\
</IT1><CAF version="1.0"><DA><RE>99999999-9</RE><RS>YYYYYYYYYYYYYYY</RS>\
<TD>10</TD><RNG><D>1</D><H>1000</H></RNG><FA>2000-01-01</FA><RSAPK><M>\
DJKFFDJKJKDJFKDJFKDJFKDJKDnbUNTAi2IaDdtAndm2p5udoqFiw==</M><E>Aw==</E></RSAPK>\
<IDK>300</IDK></DA><FRMA algoritmo="SHA1withRSA">\
J1u5/1VbPF6ASXkKoMOF0Bb9EYGVzQ1AMawDNOy0xSuAMpkyQe3yoGFthdKVK4JaypQ/F8\
afeqWjiRVMvV4+s4Q==</FRMA></CAF><TSTED>2014-04-24T12:02:20</TSTED></DD>\
<FRMT algoritmo="SHA1withRSA">jiuOQHXXcuwdpj8c510EZrCCw+pfTVGTT7obWm/\
fHlAa7j08Xff95Yb2zg31sJt6lMjSKdOK+PQp25clZuECig==</FRMT></TED>"""
result = xmltodict.parse(timbre)

server_url = {
    'SIIHOMO': 'https://maullin.sii.cl/DTEWS/',
    'SII': 'https://palena.sii.cl/DTEWS/'}

BC = '''-----BEGIN CERTIFICATE-----\n'''
EC = '''\n-----END CERTIFICATE-----\n'''

try:
    pool = urllib3.PoolManager()
except:
    pass

import os

normalize_tags = collections.OrderedDict()
normalize_tags['RutEmisor'] = [10]
normalize_tags['RznSoc'] = [100]
normalize_tags['GiroEmis'] = [80]
normalize_tags['Telefono'] = [20]
normalize_tags['CorreoEmisor'] = [80, u'variable correo del emisor']
normalize_tags['Actecos'] = collections.OrderedDict()
normalize_tags['Actecos']['Acteco'] = [6]
normalize_tags['CdgTraslado'] = [1]
normalize_tags['FolioAut'] = [5]
normalize_tags['FchAut'] = [10]
normalize_tags['Sucursal'] = [20]
normalize_tags['CdgSIISucur'] = [9]
normalize_tags['CodAdicSucur'] = [20]
normalize_tags['DirOrigen'] = [60, u'dirección de la compañía']
normalize_tags['CmnaOrigen'] = [20, u'comuna de la compañía']
normalize_tags['CiudadOrigen'] = [20, u'ciudad de la compañía']
normalize_tags['CdgVendedor'] = [60]
normalize_tags['IdAdicEmisor'] = [20]
normalize_tags['IdAdicEmisor'] = [20]
normalize_tags['RUTRecep'] = [10, u'RUT del receptor']
normalize_tags['CdgIntRecep'] = [20]
normalize_tags['RznSocRecep'] = [100, u'Razón social o nombre receptor']
normalize_tags['NumId'] = [20]
normalize_tags['Nacionalidad'] = [3]
normalize_tags['IdAdicRecep'] = [20]
normalize_tags['GiroRecep'] = [40, u'variable con giro del receptor']
normalize_tags['Contacto'] = [80]
normalize_tags['CorreoRecep'] = [80, u'variable correo del receptor']
normalize_tags['DirRecep'] = [70, u'dirección del receptor']
normalize_tags['CmnaRecep'] = [20, u'comuna del receptor']
normalize_tags['CiudadRecep'] = [20, u'ciudad del receptor']
normalize_tags['DirPostal'] = [70]
normalize_tags['CmnaPostal'] = [20]
normalize_tags['CiudadPostal'] = [20]
normalize_tags['Patente'] = [8]
normalize_tags['RUTTrans'] = [10]
normalize_tags['RUTChofer'] = [10]
normalize_tags['NombreChofer'] = [30]
normalize_tags['DirDest'] = [70]
normalize_tags['CmnaDest'] = [20]
normalize_tags['CiudadDest'] = [20]
normalize_tags['CiudadDest'] = [20]
normalize_tags['MntNeto'] = [18]
normalize_tags['MntExe'] = [18]
normalize_tags['MntBase'] = [18]
normalize_tags['MntMargenCom'] = [18]
normalize_tags['TasaIVA'] = [5]
normalize_tags['IVA'] = [18]
normalize_tags['IVAProp'] = [18]
normalize_tags['IVATerc'] = [18]
normalize_tags['TipoImp'] = [3]
normalize_tags['TasaImp'] = [5]
normalize_tags['MontoImp'] = [18]
normalize_tags['IVANoRet'] = [18]
normalize_tags['CredEC'] = [18]
normalize_tags['GmtDep'] = [18]
normalize_tags['ValComNeto'] = [18]
normalize_tags['ValComExe'] = [18]
normalize_tags['ValComIVA'] = [18]
normalize_tags['MntTotal'] = [18]
normalize_tags['MontoNF'] = [18]
normalize_tags['MontoPeriodo'] = [18]
normalize_tags['SaldoAnterior'] = [18]
normalize_tags['VlrPagar'] = [18]
normalize_tags['TpoMoneda'] = [15]
normalize_tags['TpoCambio'] = [10]
normalize_tags['MntNetoOtrMnda'] = [18]
normalize_tags['MntExeOtrMnda'] = [18]
normalize_tags['MntFaeCarneOtrMnda'] = [18]
normalize_tags['MntMargComOtrMnda'] = [18]
normalize_tags['IVAOtrMnda'] = [18]
# pluralizado deliberadamente 'Detalles' en lugar de ImptoReten
# se usó 'Detalles' (plural) para diferenciar del tag real 'Detalle'
# el cual va aplicado a cada elemento de la lista o tabla.
# según el tipo de comunicación, se elimina el tag Detalles o se le quita el
# plural en la conversion a xml
normalize_tags['NroLinDet'] = [4]
# ojo qu este que sigue es tabla tambien
normalize_tags['TpoCodigo'] = [10]
normalize_tags['VlrCodigo'] = [35]
normalize_tags['TpoDocLiq'] = [3]
normalize_tags['IndExe'] = [3]
# todo: falta retenedor
normalize_tags['NmbItem'] = [80]
normalize_tags['DscItem'] = [1000]
normalize_tags['QtyRef'] = [18]
normalize_tags['UnmdRef'] = [4]
normalize_tags['PrcRef'] = [18]
normalize_tags['QtyItem'] = [18]
# todo: falta tabla subcantidad
normalize_tags['FchElabor'] = [10]
normalize_tags['FchVencim'] = [10]
normalize_tags['UnmdItem'] = [10]
normalize_tags['PrcItem'] = [18]
# todo: falta tabla OtrMnda
normalize_tags['DescuentoOct'] = [5]
normalize_tags['DescuentoMonto'] = [18]
# todo: falta tabla distrib dcto
# todo: falta tabla distrib recargo
# todo: falta tabla cod imp adicional y retenciones
normalize_tags['MontoItem'] = [18]
# todo: falta subtotales informativos
# ojo que estos descuentos podrían ser globales más de uno,
# pero la implementación soporta uno solo
normalize_tags['NroLinDR'] = [2]
normalize_tags['TpoMov'] = [1]
normalize_tags['GlosaDR'] = [45]
normalize_tags['TpoValor'] = [1]
normalize_tags['ValorDR'] = [18]
normalize_tags['ValorDROtrMnda'] = [18]
normalize_tags['IndExeDR'] = [1]
# pluralizado deliberadamente
normalize_tags['NroLinRef'] = [2]
normalize_tags['TpoDocRef'] = [3]
normalize_tags['IndGlobal'] = [3]
normalize_tags['FolioRef'] = [18]
normalize_tags['RUTOtr'] = [10]
normalize_tags['IdAdicOtr'] = [20]
normalize_tags['FchRef'] = [10]
normalize_tags['CodRef'] = [1]
normalize_tags['RazonRef'] = [1]
# todo: faltan comisiones y otros cargos
pluralizeds = ['Actecos', 'Detalles', 'Referencias', 'ImptoRetens']

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
    'Otro': 'Error Interno.',
}
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace(
    '/models', '/static/xsd/')

class Invoice(models.Model):
    """
    Extension of data model to contain global parameters needed
    for all electronic invoice integration.
    @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    @version: 2016-06-11
    """
    _inherit = "account.invoice"

    @staticmethod
    def safe_variable(var, key):
        try:
            msg = normalize_tags[key][1]
        except:
            msg = u'variable'
        if not var:
            raise UserError(
                u'La {} no está configurada.'.format(msg))
        return var

    @staticmethod
    def get_object_record_id(inv, call_model):
        if call_model == 'stock.picking':
            try:
                return inv._context['params']['id']
            except:
                return inv._context['active_id']
        else:
            return inv.id

    @staticmethod
    def get_attachment_name(inv, call_model=''):
        if call_model == 'stock.picking':
            return 'guia-despacho'
        else:
            return inv.sii_document_class_id.name

    @staticmethod
    def time_stamp(formato='%Y-%m-%dT%H:%M:%S'):
        tz = pytz.timezone('America/Santiago')
        return datetime.now(tz).strftime(formato)

    @staticmethod
    def convert_encoding(data, new_coding='UTF-8'):
        """
        Funcion auxiliar para conversion de codificacion de strings
        proyecto experimentos_dte
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2014-12-01
        """
        encoding = cchardet.detect(data)['encoding']
        if new_coding.upper() != encoding.upper():
            data = data.decode(encoding, data).encode(new_coding)
        return data

    @staticmethod
    def set_folio(inv, folio):
        """
        Funcion para actualizar el folio tomando el valor devuelto por el
        tercera parte integrador.
        Esta funcion se usa cuando un tercero comanda los folios
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-23
        """
        # if dte in [52]:
        #     inv.voucher_ids[0].book_id.sequence_id.number_next_actual = folio
        # else:
        inv.journal_document_class_id.sequence_id.number_next_actual = folio

    @staticmethod
    def get_resolution_data(comp_id):
        """
        Funcion usada en SII
        Toma los datos referentes a la resolución SII que autoriza a
        emitir DTE
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-06-01
        """
        resolution_data = {
            'dte_resolution_date': comp_id.dte_resolution_date,
            'dte_resolution_number': comp_id.dte_resolution_number}
        return resolution_data

    @staticmethod
    def _dte_to_xml(dte, tpo_dte="Documento"):
        ted = dte[tpo_dte + ' ID']['TEDd']
        dte[(tpo_dte + ' ID')]['TEDd'] = ''
        # xml = dicttoxml.dicttoxml(
        #     dte, root=False, attr_type=False) \
        #     .replace('<item>', '').replace('</item>', '')\
        #     .replace('<reflines>', '').replace('</reflines>', '')\
        #     .replace('<TEDd>', '').replace('</TEDd>', '')\
        #     .replace('</' + tpo_dte + '_ID>', '\n'+ted+'\n</'+ tpo_dte + '_ID>')
        xml = dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).replace('<item>', '') \
            .replace('</item>', '').replace('<TEDd>', '') \
            .replace('</TEDd>', '').replace(
            '</{}_ID>'.format(tpo_dte),
            '\n{}\n</{}_ID>'.format(ted, tpo_dte))
        return xml

    def normalize_string(self, var, key, control='truncate'):
        if isinstance(key, (int, long, float, complex)):
            size = key
            control = 'truncate'
        else:
            size = normalize_tags[key][0]
        if self.company_id.dte_service_provider in ['LIBREDTE']:
            var = ld.char_replace(var)
            # var = unicodedata.normalize('NFKD', var).encode('ascii', 'ignore')
        if control == 'truncate':
            var = var[:size]
        elif control == 'safe':
            self.safe_variable(var, key)
        return var

    def get_digital_signature_pem(self, comp_id):
        obj = user = self[0].responsable_envio
        if not obj:
            obj = user = self.env.user
        if not obj.cert:
            obj = self.env['res.users'].search(
                [("authorized_users_ids", "=", user.id)])
            if not obj or not obj.cert:
                obj = self.env['res.company'].browse([comp_id.id])
                if not obj.cert or not user.id in obj.authorized_users_ids.ids:
                    return False
        signature_data = {
            'subject_name': obj.name,
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert,
            'rut_envia': obj.subject_serial_number}
        return signature_data

    def get_digital_signature(self, comp_id):
        obj = user = False
        if 'responsable_envio' in self and self._ids:
            obj = user = self[0].responsable_envio
        if not obj:
            obj = user = self.env.user
        _logger.info(obj.name)
        if not obj.cert:
            obj = self.env['res.users'].search(
                [("authorized_users_ids", "=", user.id)])
            if not obj or not obj.cert:
                obj = self.env['res.company'].browse([comp_id.id])
                if not obj.cert or not user.id in obj.authorized_users_ids.ids:
                    return False
        signature_data = {
            'subject_name': obj.name,
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert}
        return signature_data

    def get_xml_file(self):
        """
        Funcion para descargar el xml en el sistema local del usuario
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-05-01
        """
        filename = (self.document_number+'.xml').replace(' ','')
        return {
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=account.invoice\
&field=sii_xml_request&id=%s&filename=%s' % (self.id,filename),
            'target': 'self',
        }

    def get_folio(self):
        """
        Funcion para descargar el folio tomando el valor desde la secuencia
        correspondiente al tipo de documento.
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-05-01
        """
        return int(self.next_invoice_number)

    def get_folio_current(self):
        """
        Funcion para obtener el folio ya registrado en el dato
        correspondiente al tipo de documento.
        (remoción del prefijo almacenado)
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-05-01
        """
        prefix = self.journal_document_class_id.sequence_id.prefix
        try:
            folio = self.sii_document_number.replace(prefix, '', 1)
        except:
            folio = self.sii_document_number
        return int(folio)

    def get_caf_file(self):
        """
        Se Retorna el CAF que corresponda a la secuencia, independiente del
        estado ya que si se suben 2 CAF y uno está por terminar y se hace un
        evío masivo Deja fuera Los del antiguo CAF, que son válidos aún,
        porque no se han enviado; y arroja Error de que la secuencia no está
        en el rango del CAF
        """
        caffiles = self.journal_document_class_id.sequence_id.dte_caf_ids
        folio = self.get_folio()
        if not caffiles:
            raise UserError(_('''There is no CAF file available or in use \
for this Document. Please enable one.'''))
        for caffile in caffiles:
            post = base64.b64decode(caffile.caf_file)
            post = xmltodict.parse(post.replace(
                '<?xml version="1.0"?>', '', 1))
            folio_inicial = post['AUTORIZACION']['CAF']['DA']['RNG']['D']
            folio_final = post['AUTORIZACION']['CAF']['DA']['RNG']['H']
            if folio in range(int(folio_inicial), (int(folio_final)+1)):
                return post
        if folio > int(folio_final):
            msg = '''El folio de este documento: {} está fuera de rango \
del CAF vigente (desde {} hasta {}). Solicite un nuevo CAF en el sitio \
www.sii.cl'''.format(folio, folio_inicial, folio_final)
            # defino el status como "spent"
            caffile.status = 'spent'
            raise UserError(_(msg))
        return False

    def _es_boleta(self):
        if self.sii_document_class_id.sii_code in [35, 38, 39, 41, 70, 71]:
            return True
        return False

    def _giros_emisor(self):
        giros_emisor = []
        for turn in self.company_id.company_activities_ids:
            giros_emisor.extend([{'Acteco': turn.code}])
            # giros_emisor.extend([turn.code])
        return giros_emisor

    def _id_doc(self, tax_include=False, MntExe=0):
        IdDoc = collections.OrderedDict()
        IdDoc['TipoDTE'] = self.sii_document_class_id.sii_code
        IdDoc['Folio'] = self.get_folio()
        IdDoc['FchEmis'] = cm.safe_date(self.date_invoice)
        if self._es_boleta():
            IdDoc['IndServicio'] = 3
            #@TODO agregar las otras opciones a la fichade producto servicio
        if self.ticket:
            IdDoc['TpoImpresion'] = "T"
        #if self.tipo_servicio:
        #    Encabezado['IdDoc']['IndServicio'] = 1,2,3,4
        # todo: forma de pago y fecha de vencimiento - opcional
        if tax_include and MntExe == 0 and not self._es_boleta():
            IdDoc['MntBruto'] = 1
        if not self._es_boleta():
            IdDoc['FmaPago'] = self.forma_pago or 1
        if not tax_include and self._es_boleta():
            IdDoc['IndMntNeto'] = 2
        #if self._es_boleta():
            #Servicios periódicos
        #    IdDoc['PeriodoDesde'] =
        #    IdDoc['PeriodoHasta'] =
        if not self._es_boleta():
            IdDoc['FchVenc'] = self.date_due or datetime.strftime(
                datetime.now(), '%Y-%m-%d')
        return IdDoc

    def _emisor(self):
        emisor= collections.OrderedDict()
        emisor['RUTEmisor'] = cm.format_vat(self.company_id.vat)
        if self._es_boleta():
            emisor['RznSocEmisor'] = self.normalize_string(
                self.company_id.partner_id.name, 'RznSoc', 'safe')
            # emisor['GiroEmisor'] = self.normalize_string(
            #     self.company_id.activity_description.name, 'GiroEmis', 'safe')
            emisor['GiroEmis'] = self.normalize_string(
                self.turn_issuer.name, 'GiroEmis', 'safe')
        else:
            emisor['RznSoc'] = self.normalize_string(
                self.company_id.partner_id.name, 'RznSoc', 'safe')
            # emisor['GiroEmis'] = self.normalize_string(
            #     self.company_id.activity_description.name, 'GiroEmis', 'safe')
            emisor['GiroEmis'] = self.normalize_string(
                self.turn_issuer.name, 'GiroEmis', 'safe')
            emisor['Telefono'] = self.normalize_string(
                self.company_id.phone or '', 'Telefono', 'truncate')
            emisor['CorreoEmisor'] = self.normalize_string(
                self.company_id.dte_email, 'CorreoEmisor', 'safe')
            emisor['Actecos'] = self._giros_emisor()
        if self.journal_id.sii_code:
            emisor['Sucursal'] = self.normalize_string(
                self.journal_id.sucursal.name, 'Sucursal', 'truncate')
            emisor['CdgSIISucur'] = self.normalize_string(
                self.journal_id.sii_code or '', 'CdgSIISucur', 'truncate')
        emisor['DirOrigen'] = self.normalize_string('{} {}'.format(
            self.company_id.street or '', self.company_id.street2 or ''),
            'DirOrigen', 'safe')
        emisor['CmnaOrigen'] = self.normalize_string(
            self.company_id.city_id.name, 'CmnaOrigen', 'safe')
        emisor['CiudadOrigen'] = self.normalize_string(
            self.company_id.city, 'CiudadOrigen', 'safe')
        return emisor

    def _receptor(self):
        receptor = collections.OrderedDict()
        if not self.partner_id.vat and not self._es_boleta():
            raise UserError("Debe Ingresar RUT Receptor")
        # if self._es_boleta():
        #     receptor['CdgIntRecep']
        receptor['RUTRecep'] = cm.format_vat(self.partner_id.vat)
        receptor['RznSocRecep'] = self.normalize_string(
            self.partner_id.name, 'RznSocRecep', 'safe')
        if not self._es_boleta():
            # if not self.activity_description:
            #    raise UserError(_('Seleccione giro del partner.'))
            # receptor['GiroRecep'] = self.normalize_string(
            #     self.activity_description.name, 'GiroRecep', 'safe')
            receptor['GiroRecep'] = self.normalize_string(
                self.invoice_turn.name, 'GiroRecep', 'safe')
        if self.partner_id.phone:
            receptor['Contacto'] = self.normalize_string(
                self.partner_id.phone, 'Contacto', 'truncate')
        if self.partner_id.dte_email and not self._es_boleta():
            receptor['CorreoRecep'] = self.partner_id.dte_email
        receptor['DirRecep'] = self.normalize_string('{} {}'.format(
            self.partner_id.street or '',
            self.partner_id.street2 or ''), 'DirRecep', 'safe')
        receptor['CmnaRecep'] = self.normalize_string(
            self.partner_id.city_id.name, 'CmnaRecep', 'safe')
        receptor['CiudadRecep'] = self.normalize_string(
            self.partner_id.city, 'CiudadRecep', 'safe')
        return receptor

    def _totales(self, MntExe=0, no_product=False, tax_include=False):
        Totales = collections.OrderedDict()
        if self.sii_document_class_id.sii_code == 34 or (
                self.referencias and self.referencias[0].
                sii_referencia_TpoDocRef.sii_code == '34'):
            Totales['MntExe'] = int(round(self.amount_total, 0))
            if no_product:
                Totales['MntExe'] = 0
        elif self.amount_untaxed and self.amount_untaxed != 0:
            if not self._es_boleta() or not tax_include:
                IVA = False
                for t in self.tax_line_ids:
                    if t.tax_id.sii_code in [14, 15]:
                        IVA = t
                if IVA and IVA.base > 0:
                    Totales['MntNeto'] = int(round((IVA.base), 0))
            if MntExe > 0:
                Totales['MntExe'] = int(round( MntExe))
            if not self._es_boleta() or not tax_include:
                if IVA:
                    if not self._es_boleta():
                        Totales['TasaIVA'] = round(IVA.tax_id.amount,2)
                    Totales['IVA'] = int(round(IVA.amount, 0))
                if no_product:
                    Totales['MntNeto'] = 0
                    if not self._es_boleta():
                        Totales['TasaIVA'] = 0
                    Totales['IVA'] = 0
            if IVA and IVA.tax_id.sii_code in [15]:
                Totales['ImptoReten'] = collections.OrderedDict()
                Totales['ImptoReten']['TpoImp'] = IVA.tax_id.sii_code
                Totales['ImptoReten']['TasaImp'] = round(IVA.tax_id.amount,2)
                Totales['ImptoReten']['MontoImp'] = int(round(IVA.amount))
        monto_total = int(round(self.amount_total, 0))
        if no_product:
            monto_total = 0
        Totales['MntTotal'] = monto_total

        #Totales['MontoNF']
        #Totales['TotalPeriodo']
        #Totales['SaldoAnterior']
        #Totales['VlrPagar']
        return Totales

    def _encabezado(self, MntExe=0, no_product=False, tax_include=False):
        encabezado = collections.OrderedDict()
        encabezado['IdDoc'] = self._id_doc(tax_include, MntExe)
        encabezado['Emisor'] = self._emisor()
        encabezado['Receptor'] = self._receptor()
        if self.company_id.dte_service_provider not in ['LIBREDTE']:
            encabezado['Totales'] = self._totales(MntExe, no_product)
        return encabezado

    def create_headers_ldte(self, comp_id=False):
        """
        Función para crear los headers necesarios por LibreDTE
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-23
        """
        if comp_id:
            dte_username = comp_id.dte_username
            dte_password = comp_id.dte_password
        else:
            dte_username = self.company_id.dte_username
            dte_password = self.company_id.dte_password
        headers = {}
        headers['Authorization'] = 'Basic {}'.format(
            base64.b64encode('{}:{}'.format(
                dte_password, dte_username)))
        # control del header
        # raise UserError(headers['Authorization'])
        headers['Accept-Encoding'] = 'gzip, deflate, identity'
        headers['Accept'] = '*/*'
        headers['User-Agent'] = 'python-requests/2.6.0 CPython/2.7.6 \
Linux/3.13.0-88-generic'
        headers['Connection'] = 'keep-alive'
        headers['Content-Type'] = 'application/json'
        return headers

    def _invoice_lines(self):
        line_number = 1
        invoice_lines = []
        no_product = False
        MntExe = 0
        for line in self.invoice_line_ids:
            if line.product_id.default_code == 'NO_PRODUCT':
                no_product = True
            lines = collections.OrderedDict()
            lines['NroLinDet'] = line_number
            if line.product_id.default_code and not no_product:
                lines['CdgItem'] = collections.OrderedDict()
                lines['CdgItem']['TpoCodigo'] = 'INT1'
                lines['CdgItem']['VlrCodigo'] = line.product_id.default_code
            tax_include = False
            for t in line.invoice_line_tax_ids:
                tax_include = t.price_include
                if t.amount == 0 or t.sii_code in [0]:
                    # TODO: mejor manera de identificar exento de afecto
                    lines['IndExe'] = 1
                    MntExe += int(round(line.price_tax_included, 0))
            if not tax_include:
                lines['IndExe'] = 1
                MntExe += int(round(line.price_tax_included, 0))
                # if line.product_id.type == 'events':
                #   lines['ItemEspectaculo'] =
                #            if self._es_boleta():
                #                lines['RUTMandante']
            lines['NmbItem'] = self.normalize_string(
                line.product_id.name, 'NmbItem', 'safe')
            lines['DscItem'] = self.normalize_string(
                line.name, 'DscItem', 'truncate')
            # descripción más extensa
            if line.product_id.default_code:
                lines['NmbItem'] = self.normalize_string(
                    line.product_id.name.replace(
                        '[' + line.product_id.default_code + '] ', ''),
                    'NmbItem', 'truncate')
            # lines['InfoTicket']
            qty = round(line.quantity, 4)
            if not no_product:
                lines['QtyItem'] = qty
            if qty == 0 and not no_product:
                lines['QtyItem'] = 1
            elif qty < 0:
                raise UserError("NO puede ser menor que 0")
            if not no_product:
                lines['UnmdItem'] = line.uom_id.name[:4]
                lines['PrcItem'] = round(line.price_unit, 4)
            if line.discount > 0:
                lines['DescuentoPct'] = line.discount
                lines['DescuentoMonto'] = int(
                    round(
                        (((line.discount / 100) * lines['PrcItem']) * qty)))
            if not no_product and not tax_include:
                lines['MontoItem'] = int(round(line.price_subtotal, 0))
            elif not no_product:
                lines['MontoItem'] = int(round(line.price_tax_included, 0))
            if no_product:
                lines['MontoItem'] = 0
            line_number += 1
            invoice_lines.extend([{'Detalle': lines}])
            if 'IndExe' in lines:
                tax_include = False
        return {
            'invoice_lines': invoice_lines,
            'MntExe': MntExe,
            'no_product': no_product,
            'tax_include': tax_include}

    def _dte(self, n_atencion=None):
        dte = collections.OrderedDict()
        invoice_lines = self._invoice_lines()
        dte['Encabezado'] = self._encabezado(
            invoice_lines['MntExe'], invoice_lines['no_product'],
            invoice_lines['tax_include'])
        lin_ref = 1
        ref_lines = []
        if self.company_id.dte_service_provider == 'SIIHOMO' and isinstance(
                n_atencion, unicode) and n_atencion != '' and \
                not self._es_boleta():
            ref_line = collections.OrderedDict()
            ref_line['NroLinRef'] = lin_ref
            ref_line['TpoDocRef'] = "SET"
            ref_line['FolioRef'] = self.get_folio()
            ref_line['FchRef'] = datetime.strftime(datetime.now(),
                                                   '%Y-%m-%d')
            ref_line['RazonRef'] = "CASO " + n_atencion + "-" + str(
                self.sii_batch_number)
            lin_ref += 1
            # ref_lines.extend([ref_line])
            ref_lines.extend([{'Referencia': ref_line}])
        # raise UserError('referencias...: {}, ref anteriores'.format(
        #     self.referencias, json.dumps(ref_lines)))
        if self.referencias:
            for ref in self.referencias:
                ref_line = collections.OrderedDict()
                ref_line['NroLinRef'] = lin_ref
                if not self._es_boleta():
                    if ref.sii_referencia_TpoDocRef:
                        ref_line['TpoDocRef'] = \
                            ref.sii_referencia_TpoDocRef.sii_code
                        ref_line['FolioRef'] = ref.origen
                    ref_line['FchRef'] = ref.fecha_documento or \
                                         datetime.strftime(
                                             datetime.now(), '%Y-%m-%d')
                if ref.sii_referencia_CodRef not in ['', 'none', False]:
                    ref_line['CodRef'] = ref.sii_referencia_CodRef
                ref_line['RazonRef'] = ref.motivo
                if self._es_boleta():
                    ref_line['CodVndor'] = self.seler_id.id
                    ref_lines[
                        'CodCaja'] = self.journal_id.point_of_sale_id.name
                ref_lines.extend([{'Referencia': ref_line}])
                lin_ref += 1
        dte['Detalles'] = invoice_lines['invoice_lines']
        if len(ref_lines) > 0:
            dte['Referencias'] = ref_lines
        if self.company_id.dte_service_provider not in ['LIBREDTE']:
            dte['TEDd'] = self.get_barcode(invoice_lines['no_product'])
        _logger.info('DTE _dte...{}'.format(json.dumps(dte)))
        # raise UserError('stop dentro _dte')
        return dte

    def _tpo_dte(self):
        tpo_dte = "Documento"
        if self.sii_document_class_id.sii_code == 43:
            tpo_dte = 'Liquidacion'
        return tpo_dte

    def _timbrar(self, n_atencion=None):
        try:
            signature_d = self.get_digital_signature(self.company_id)
        except:
            raise UserError(_('''There is no Signer Person with an \
authorized signature for you in the system. Please make sure that \
'user_signature_key' module has been installed and enable a digital \
signature, for you or make the signer to authorize you to use his \
signature.'''))
        certp = signature_d['cert'].replace(
            BC, '').replace(EC, '').replace('\n', '')
        folio = self.get_folio()
        tpo_dte = self._tpo_dte()
        doc_id_number = "F{}T{}".format(
            folio, self.sii_document_class_id.sii_code)
        doc_id = '<' + tpo_dte + ' ID="{}">'.format(doc_id_number)
        dte = collections.OrderedDict()
        dte[(tpo_dte + ' ID')] = self._dte(n_atencion)
        # raise UserError('dte timbrado: {}'.format(json.dumps(dte)))
        xml = self._dte_to_xml(dte, tpo_dte)
        root = etree.XML(xml)
        xml_pret = etree.tostring(root, pretty_print=True).replace(
            '<' + tpo_dte + '_ID>', doc_id).replace(
            '</' + tpo_dte + '_ID>', '</' + tpo_dte + '>')
        envelope_efact = self.convert_encoding(xml_pret, 'ISO-8859-1')
        envelope_efact = si.create_template_doc(envelope_efact)
        _logger.info('envelope_efact: {}'.format(envelope_efact))
        raise UserError('_timbrar: envelope_efact')
        # type = 'doc'
        type = 'bol' if self._es_boleta() else 'doc'
        #    type = 'bol'
        einvoice = si.sign_full_xml(
            envelope_efact, signature_d['priv_key'],
            si.split_cert(certp), doc_id_number, type)
        raise UserError('envelope_efact: {}'.format(envelope_efact))
        self.sii_xml_request = einvoice

    def _get_send_status(self, track_id, signature_d, token):
        url = server_url[
                  self.company_id.dte_service_provider] + 'QueryEstUp.jws?WSDL'
        ns = 'urn:' + server_url[
            self.company_id.dte_service_provider] + 'QueryEstUp.jws'
        _server = SOAPProxy(url, ns)
        rut = cm.format_vat(self.company_id.vat)
        respuesta = _server.getEstUp(rut[:8], str(rut[-1]), track_id, token)
        self.sii_receipt = respuesta
        resp = xmltodict.parse(respuesta)
        status = False
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "-11":
            if resp['SII:RESPUESTA']['SII:RESP_HDR']['ERR_CODE'] == "2":
                status = {'warning': {'title': _('Estado -11'),
                                      'message': _('''Estado -11: Espere a que \
sea aceptado por el SII, intente en 5s más''')}}
            else:
                status = {'warning': {'title': _('Estado -11'),
                                      'message': _('''Estado -11: error \
Algo a salido mal, revisar carátula''')}}
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "EPR":
            self.sii_result = "Proceso"
            if resp['SII:RESPUESTA']['SII:RESP_BODY']['RECHAZADOS'] == "1":
                self.sii_result = "Rechazado"
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "RCT":
            self.sii_result = "Rechazado"
            _logger.info(resp)
            status = {
                'warning': {'title': _('Error RCT'),
                            'message': _(resp['SII:RESPUESTA']['GLOSA'])}}
        return status

    def _get_dte_status(self, signature_d, token):
        """
        Para SII
        :param signature_d:
        :param token:
        :return:
        """
        url = server_url[
                  self.company_id.dte_service_provider] + 'QueryEstDte.jws?WSDL'
        ns = 'urn:' + server_url[
            self.company_id.dte_service_provider] + 'QueryEstDte.jws'
        _server = SOAPProxy(url, ns)
        receptor = cm.format_vat(self.partner_id.vat)
        date_invoice = datetime.strptime(
            self.date_invoice, "%Y-%m-%d").strftime("%d-%m-%Y")
        rut = signature_d['subject_serial_number']
        respuesta = _server.getEstDte(
            rut[:8], str(rut[-1]), self.company_id.vat[2:-1],
            self.company_id.vat[-1], receptor[:8], receptor[2:-1],
            str(self.sii_document_class_id.sii_code),
            str(self.sii_document_number), date_invoice,
            str(self.amount_total), token)
        self.sii_message = respuesta
        resp = xmltodict.parse(respuesta)
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == '2':
            status = {
                'warning': {
                    'title': _("Error code: 2"),
                    'message': _(
                        resp['SII:RESPUESTA']['SII:RESP_HDR']['GLOSA'])}}
            return status
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "EPR":
            self.sii_result = "Proceso"
            if resp['SII:RESPUESTA']['SII:RESP_BODY']['RECHAZADOS'] == "1":
                self.sii_result = "Rechazado"
            if resp['SII:RESPUESTA']['SII:RESP_BODY']['REPARO'] == "1":
                self.sii_result = "Reparo"
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "RCT":
            self.sii_result = "Rechazado"

    def _check_ldte_status(self, inv='', foliop='', headers=''):
        """
        obtener estado de DTE (libreDTE).
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2017-02-11
        """
        try:
            folio = self.get_folio_current()
        except:
            try:
                if not folio:
                    folio = foliop
            except:
                folio = foliop
        if headers == '':
            headers = self.create_headers_ldte(comp_id=self.company_id)
        metodo = 1
        response_status = pool.urlopen('GET', '{}{}/{}/{}'.format(
            ld.api_upd_status,
            str(self.sii_document_class_id.sii_code),
            str(folio),
            str(cm.format_vat(self.company_id.vat)).replace(
                '-', '')[:-1]), headers=headers)
        if response_status.status != 200:
            raise UserError(
                'Error al obtener el estado del DTE emitido: {}'.format(
                    repr(response_status.data)))
        _logger.info('Se recibió una respuesta:')
        _logger.info(response_status.data)
        response_status_j = json.loads(response_status.data)
        _logger.info(response_status_j['track_id'])
        _logger.info(response_status_j['revision_estado'])
        _logger.info(response_status_j['revision_detalle'])
        if response_status_j['revision_estado'] in [
            'DTE aceptado'] or \
                        response_status_j[
                            'revision_detalle'] == 'DTE aceptado':
            resultado_status = 'Aceptado'
        elif response_status_j['revision_estado'] in \
                ['RLV - DTE Aceptado con Reparos Leves']:
            resultado_status = 'Reparo'
        elif response_status_j['revision_estado'][:3] in \
                ['SOK', 'CRT', 'PDR', 'FOK', '-11']:
            resultado_status = 'Proceso'
            _logger.info('Atención: Revisión en Proceso')
        elif response_status_j['revision_estado'] in \
                ['RCH - DTE Rechazado',
                 'RFR - Rechazado por Error en Firma',
                 'RSC - Rechazado por Error en Schema',
                 'RCT - Rechazado por Error en Carátula']:
            resultado_status = 'Rechazado'
        else:
            resultado_status = self.sii_result
        _logger.info('a grabar resultado_status: {}'.format(
            resultado_status))
        setenvio = {
            'sii_xml_response': response_status.data,
            'sii_result': resultado_status,
            'invoice_printed': 'printed'}
        self.write(setenvio)
        _logger.info(
            'resultado_status grabado: {}'.format(self.sii_result))
        _logger.info(response_status_j['revision_estado'])

    @api.multi
    def do_dte_send(self, n_atencion=None):
        """
        Este proceso sirve para manejar los envíos desde la cola de envíos
        :param n_atencion:
        :return:
        """
        dicttoxml.set_debug(False)
        DTEs = {}
        clases = {}
        company_id = False
        es_boleta = False
        batch = 0
        for inv in self.with_context(lang='es_CL'):
            if not inv.sii_batch_number or inv.sii_batch_number == 0:
                batch += 1
                inv.sii_batch_number = batch
                # si viene una guía/nota regferenciando una factura,
                # que por numeración viene a continuación de la guia/nota,
                # será recahazada laguía porque debe estar declarada la
                # factura primero
            es_boleta = inv._es_boleta()
            if inv.company_id.dte_service_provider in ['SII', 'SIIHOMO']:
                raise UserError(inv.company_id.dte_service_provider)
                try:
                    signature_d = self.get_digital_signature(inv.company_id)
                except:
                    raise UserError(_('''There is no Signer Person with an \
authorized signature for you in the system. Please make sure that \
'user_signature_key' module has been installed and enable a digital signature,
for you or make the signer to authorize you to use his signature.'''))
                certp = signature_d['cert'].replace(
                    BC, '').replace(EC, '').replace('\n', '')
                # Retimbrar con número de atención y envío
                inv._timbrar(n_atencion)
            elif inv.company_id.dte_service_provider == 'LIBREDTE':
                raise UserError(inv._dte(n_atencion))
            # @TODO Mejarorar esto en lo posible
            if not inv.sii_document_class_id.sii_code in clases:
                clases[inv.sii_document_class_id.sii_code] = []
            clases[
                inv.sii_document_class_id.sii_code].extend(
                [{'id': inv.id,
                  'envio': inv.sii_xml_request,
                  'sii_batch_number': inv.sii_batch_number,
                  'sii_document_number': inv.sii_document_number}])
            DTEs.update(clases)
            if not company_id:
                company_id = inv.company_id
            elif company_id.id != inv.company_id.id:
                raise UserError('Está combinando compañías, no está permitido \
hacer eso en un envío')
            company_id = inv.company_id
            # @TODO hacer autoreconciliación
        file_name = ""
        dtes = {}
        SubTotDTE = ''
        resol_data = self.get_resolution_data(company_id)
        signature_d = self.get_digital_signature(company_id)
        RUTEmisor = cm.format_vat(company_id.vat)
        for id_class_doc, classes in clases.iteritems():
            NroDte = 0
            for documento in classes:
                if documento['sii_batch_number'] in dtes.iterkeys():
                    raise UserError(
                        "No se puede repetir el mismo número de orden")
                dtes.update(
                    {str(documento['sii_batch_number']): documento[
                        'envio']})
                NroDte += 1
                file_name += 'F' + str(
                    int(documento['sii_document_number'])) + 'T' + str(
                    id_class_doc)
            SubTotDTE += '<SubTotDTE>\n<TpoDTE>' + str(
                id_class_doc) + '''</TpoDTE>
<NroDTE>'+str(NroDte)+'</NroDTE>
</SubTotDTE>
'''
        file_name += '.xml'
        documentos = ''
        for key in sorted(dtes.iterkeys()):
            documentos += '\n' + dtes[key]
        # firma del sobre
        RUTRecep = "60803000-K"
        # RUT SII
        dtes = si.create_template_envio(RUTEmisor, RUTRecep,
                                        resol_data['dte_resolution_date'],
                                        resol_data['dte_resolution_number'],
                                        self.time_stamp(), documentos,
                                        signature_d, SubTotDTE)
        env = 'env'
        if es_boleta:
            envio_dte = si.create_template_env(dtes, 'BOLETA')
            env = 'env_boleta'
        else:
            envio_dte = si.create_template_env(dtes)
        envio_dte = si.sign_full_xml(
            envio_dte, signature_d['priv_key'], certp,
            'SetDoc', env)
        result = si.send_xml_file(envio_dte, file_name, company_id)
        for inv in self:
            inv.write({'sii_xml_response': result['sii_xml_response'],
                       'sii_send_ident': result['sii_send_ident'],
                       'sii_result': result['sii_result'],
                       'sii_xml_request': envio_dte,
                       'sii_send_file_name': file_name})

    @api.multi
    def ask_for_dte_status(self):
        """
        Este proceso realiza las consultas desde la cola de envío.
        :return:
        """
        if self.company_id.dte_service_provider not in ['LIBREDTE']:
            try:
                signature_d = self.get_digital_signature_pem(
                    self.company_id)
                seed = si.get_seed(self.company_id)
                template_string = si.create_template_seed(seed)
                seed_firmado = si.sign_seed(
                    template_string, signature_d['priv_key'],
                    signature_d['cert'])
                token = si.get_token(seed_firmado, self.company_id)
            except:
                _logger.info('ask_for_dte_status: no se pudo enviar')
                raise UserError('ask_for_dte_status: no se pudo enviar')
            if self.sii_result == 'Enviado':
                status = self._get_send_status(
                    self.sii_send_ident, signature_d, token)
                if self.sii_result != 'Proceso':
                    return status
            return self._get_dte_status(signature_d, token)
        else:
            self._check_ldte_status()
            _logger.info(
                'ask_for_dte_status: (check) intento para LibreDTE')
        if not self.sii_send_ident:
            raise UserError('''No se ha enviado aún el documento, aún está en \
cola de envío interna en odoo''')

    """
    Definicion de extension de modelo de datos para account.invoice
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2015-02-01
    """
    sii_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True,
        help='Batch number for processing multiple invoices together')
    sii_barcode = fields.Char(
        copy=False,
        string=_('SII Barcode'),
        readonly=True,
        help='SII Barcode Name')
    sii_barcode_img = fields.Binary(
        copy=False,
        string=_('SII Barcode Image'),
        readonly=True,
        help='SII Barcode Image in PDF417 format')
    sii_receipt = fields.Text(
        string='SII Mensaje de recepción',
        copy=False)
    sii_message = fields.Text(
        string='SII Message',
        copy=False)
    sii_xml_request = fields.Text(
        string='SII XML Request',
        copy=False)
    sii_xml_response = fields.Text(
        string='SII XML Response',
        copy=False)
    sii_send_ident = fields.Text(
        string='SII Send Identification',
        copy=False)
    sii_result = fields.Selection([
        ('', 'n/a'),
        ('NoEnviado', 'No Enviado'),
        ('EnCola','En cola de envío'),
        ('Enviado', 'Enviado'),
        ('Aceptado', 'Aceptado'),
        ('Rechazado', 'Rechazado'),
        ('Reparo', 'Reparo'),
        ('Proceso', 'Proceso'),
        ('Reenviar', 'Reenviar'),
        ('Anulado', 'Anulado')],
        'Resultado',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        help="SII request result",
        default = '')
    canceled = fields.Boolean(string="Canceled?")
    estado_recep_dte = fields.Selection(
        [
            ('no_revisado','No Revisado'),
            ('0','Conforme'),
            ('1','Error de Schema'),
            ('2','Error de Firma'),
            ('3','RUT Receptor No Corresponde'),
            ('90','Archivo Repetido'),
            ('91','Archivo Ilegible'),
            ('99','Envio Rechazado - Otros')
        ],string="Estado de Recepcion del Envio")
    estado_recep_glosa = fields.Char(string="Información Adicional del Estado de Recepción")
    sii_send_file_name = fields.Char(string="Send File Name")
    responsable_envio = fields.Many2one('res.users')
    ticket = fields.Boolean(string="Formato Ticket",
            default=False,
            readonly=True,
            states={'draft': [('readonly', False)]})

    @api.multi
    def get_related_invoices_data(self):
        """
        List related invoice information to fill CbtesAsoc.
        """
        self.ensure_one()
        rel_invoices = self.search([
            ('number', '=', self.origin),
            ('state', 'not in',
                ['draft', 'proforma', 'proforma2', 'cancel'])])
        return rel_invoices

    @api.multi
    def bring_generated_xml_ldte(self, foliop=0, headers='', call_model=''):
        """
        Función para traer el XML que ya fué generado anteriormente, y sobre
        el cual existe un track id.
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-12-16
        :return:
        """
        if call_model == 'stock.picking' or \
                        self._context['active_model'] == 'stock.picking':
            inv = self.env['stock.picking'].browse(
                self._context['active_id'])
            sii_code = 52
        else:
            self.ensure_one()
            inv = self
            sii_code = inv.sii_document_class_id.sii_code
            folio = self.get_folio_current()
        try:
            if not folio:
                folio = foliop
        except:
            folio = foliop
        emisor = cm.format_vat(inv.company_id.vat)
        _logger.info('entrada a bring_generated_xml_ldte. Folio: {}'.format(
            folio))
        if headers == '':
            headers = self.create_headers_ldte()
        _logger.info('headers: {}'.format(headers))
        _logger.info(ld.api_get_xml.format(sii_code, folio, emisor))
        response_xml = pool.urlopen(
            'GET', ld.api_get_xml.format(sii_code, folio, emisor), headers=headers)
        if response_xml.status != 200:
            raise UserError('Error: {}'.format(response_xml.data))
        _logger.info('response_generar: {}'.format(
            base64.b64decode(response_xml.data)))
        inv.sii_xml_request = base64.b64decode(response_xml.data)
        attachment_obj = self.env['ir.attachment']
        _logger.info('Attachment')
        attachment_name = self.get_attachment_name(
            inv, call_model=str(inv._name))
        record_id = self.get_object_record_id(inv, call_model=str(inv._name))
        _logger.info(attachment_name)
        attachment_id = attachment_obj.create(
            {
                'name': 'DTE_'+attachment_name+'-'+str(
                    folio)+'.xml',
                'datas': response_xml.data,
                'datas_fname': 'DTE_'+attachment_name+'-'+str(
                    folio)+'.xml',
                'res_model': str(inv._name),
                'res_id': record_id,
                'type': 'binary'
            })
        _logger.info(
            'Se ha generado factura en XML con el id {} para el id {}'.format(
            attachment_id, record_id))

    @api.multi
    def bring_xml_ldte(self, inv, response_emitir_data, headers=''):
        """
        Función para tomar el XML generado en libreDTE y adjuntarlo al registro
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-23
        """
        _logger.info('entrada a bringxml function')
        if headers == '':
            headers = self.create_headers_ldte()
        _logger.info('api: {}, headers: {}, body: {}'.format(
            ld.api_generar, headers, response_emitir_data))
        response_generar = pool.urlopen(
            'POST', ld.api_generar, headers=headers,
            body=response_emitir_data)
        if response_generar.status != 200:
            raise UserError('Error en conexión al generar: {}, {}'.format(
                response_generar.status, response_generar.data))
        _logger.info('response_generar: {}'.format(response_generar.data))
        inv.sii_xml_response = response_emitir_data
        try:
            response_j = json.loads(response_generar.data)
        except:
            raise UserError('LibreDTE No pudo generar el XML.\n'
                'Reintente en un instante. \n{}'.format(
                response_generar.data))
        _logger.info('Folio desde response_j: {}, tipo dte: {}'.format(
            response_j['folio'], response_j['dte']))
        if not response_j['xml']:
            if True:
                if True:
                    _logger.info(
                        'intentando traer el xml. headers: {}, folio: {}'.
                        format(headers, int(response_j['folio'])))
                    response_j['xml'] = self.bring_generated_xml_ldte(
                        int(response_j['folio']), headers=headers)
                else:
                    raise UserError(
                        'No se pudo recibir el XML del documento. Sin embargo, \
este puede haber sido generado en LibreDTE. coloque el folio en el campo \
TRACKID antes de revalidar, reintente la validación.')
            else:
                raise UserError('bring_gen: no pudo traer el xml')
        else:
            attachment_obj = self.env['ir.attachment']
            _logger.info('Attachment')
            _logger.info(inv.sii_document_class_id.name)
            _logger.info(response_j['folio'])
            attachment_id = attachment_obj.create(
                {
                    'name': 'DTE_'+inv.sii_document_class_id.name+'-'+str(
                        response_j['folio'])+'.xml',
                    'datas': response_j['xml'],
                    'datas_fname': 'DTE_'+inv.sii_document_class_id.name+'-'+str(
                        response_j['folio'])+'.xml',
                    'res_model': inv._name,
                    'res_id': inv.id,
                    'type': 'binary'
                })
            _logger.info('Se ha generado factura en XML con el id {}'.format(
                attachment_id))
        return response_j

    @api.multi
    def get_xml_attachment(self, inv=''):
        """
        Función para leer el xml para libreDTE desde los attachments
        @author: Daniel Blanco Martín (daniel[at]blancomartin.cl)
        @version: 2016-07-01
        """
        # self.ensure_one()
        if inv == '':
            inv = self
        _logger.info('entrando a la funcion de toma de xml desde attachments')
        xml_attachment = ''
        attachment_id = self.env['ir.attachment'].search([
            ('res_model', '=', inv._name),
            ('res_id', '=', inv.id,),
            ('name', 'like', 'DTE_'),
            ('name', 'ilike', '.xml')])

        for att_id in attachment_id:
            _logger.info(att_id.id)
            xml_attachment = att_id.datas
            break
        return xml_attachment

    @api.multi
    def bring_pdf_ldte(self, foliop='', headers='', call_model=''):
        """
        Función para tomar el PDF generado en libreDTE y adjuntarlo al registro
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-23
        Se corrige función para que no cree un nuevo PDF cada vez que se hace
        clic en botón
        y no tome PDF con cedible que se creará en botón imprimir.
        @review: Juan Plaza (jplaza@isos.cl)
        @version: 2016-09-28
        """
        _logger.info('bring_pdf_ldte.. call_model: {}'.format(call_model))
        attachment_obj = self.env['ir.attachment']
        if attachment_obj.search(
                [('res_model', '=', self._name), ('res_id', '=', self.id,),
                 ('name', 'like', 'DTE_'),
                 ('name', 'not like', 'cedible'), ('name', 'ilike', '.pdf')]):
            pass
        else:
            if call_model == 'stock.picking':
                _logger.info(
                    'contexto en bring_pdf_ldte: {}'.format(self._context))
                inv = self.env['stock.picking'].browse(
                    self._context['active_id'])
                sii_code = 52
            else:
                self.ensure_one()
                inv = self
                sii_code = inv.sii_document_class_id.sii_code
                folio = self.get_folio_current()
            try:
                if not folio:
                    folio = foliop
            except:
                folio = foliop

            _logger.info('entrada a bringpdf function')
            if not headers:
                headers = self.create_headers_ldte(comp_id=self.company_id)
            # en lugar de third_party_xml, que ahora no va a existir más,
            # hay que tomar el xml del adjunto, o bien del texto
            # pero prefiero del adjunto
            dte_xml = self.get_xml_attachment(inv)
            dte_tributarias = self.company_id.dte_tributarias \
                if self.company_id.dte_tributarias else 1
            dte_cedibles = self.company_id.dte_cedibles \
                if self.company_id.dte_cedibles else 0
            generar_pdf_request = json.dumps(
                {'xml': dte_xml,
                 'cedible': 1 if dte_cedibles > 0 else 0,
                 'copias_tributarias': dte_tributarias,
                 'copias_cedibles': dte_cedibles,
                 'compress': False})
            _logger.info(generar_pdf_request)
            response_pdf = pool.urlopen(
                'POST', ld.api_gen_pdf, headers=headers,
                body=generar_pdf_request)
            if response_pdf.status != 200:
                raise UserError('Error en conexión al generar: {}, {}'.format(
                    response_pdf.status, response_pdf.data))
            invoice_pdf = base64.b64encode(response_pdf.data)
            # raise UserError(inv._name)
            attachment_name = self.get_attachment_name(
                inv, call_model=str(inv._name))
            attachment_obj = self.env['ir.attachment']
            # raise UserError(inv._name, inv.id, inv._context)
            record_id = self.get_object_record_id(
                inv, call_model=str(inv._name))
            attachment_id = attachment_obj.create(
                {
                    'name': 'DTE_' + attachment_name +
                            '-' + str(folio) + '.pdf',
                    'datas': invoice_pdf,
                    'datas_fname': 'DTE_' + attachment_name +
                                   '-' + str(folio) + '.pdf',
                    'res_model': inv._name,
                    'res_id': record_id,
                    'type': 'binary'})
            _logger.info('attachment pdf')
            _logger.info(attachment_name)
            _logger.info(attachment_id)
            _logger.info(record_id)

    @api.multi
    def action_invoice_open(self):
        for inv in self:
            inv.sii_result = 'NoEnviado'
            inv.responsable_envio = self.env.user.id
            if inv.type in ['out_invoice', 'out_refund'] and \
                    inv.company_id.dte_service_provider in ['SII', 'SIIHOMO']:
                inv._timbrar()
            else:
                tpo_dte = inv._tpo_dte()
                dte = inv._dte()
                dte[(tpo_dte + ' ID')] = dte
                _logger.info('dte desde action_invoice_open'.format(dte))
                raise UserError('ver dte a enviar')
        super(Invoice, self).action_invoice_open()

    @api.multi
    def do_dte_send_invoice(self, n_atencion=None):
        if self.company_id.dte_service_provider not in ['LIBREDTE']:
            for inv in self:
                if inv.sii_result not in ['', 'NoEnviado', 'Rechazado']:
                    raise UserError(
                        u"El documento {} ya ha sido enviado o está en cola de \
    envío".format(inv.sii_document_number))
                if inv.sii_result in ['Rechazado']:
                    inv._timbrar()
                inv.responsable_envio = self.env.user.id
                inv.sii_result = 'EnCola'
            if not isinstance(n_atencion, unicode):
                n_atencion = ''
            self.env['sii.cola_envio'].create({
                                        'doc_ids': self.ids,
                                        'model': 'account.invoice',
                                        'user_id': self.env.user.id,
                                        'tipo_trabajo': 'envio',
                                        'n_atencion': n_atencion})
        else:
            self.ensure_one()
            headers = self.create_headers_ldte()
            _logger.info('Headers: {}'.format(headers))
            _logger.info('DTE enviado json:'.format(json.dumps(dte)))
            raise UserError('do_dte_send_invoice sale por ldte')
            response_j = ld.enviar_ldte(inv, dte, headers)
            inv.write(
                {
                    'sii_result': 'Enviado',
                    'sii_send_ident': response_j['track_id']})
            _logger.info('se guardó xml con la factura')
            self.set_folio(inv, response_j['folio'])

    @api.multi
    def get_barcode(self, no_product=False):
        ted = False
        folio = self.get_folio()
        result['TED']['DD']['RE'] = cm.format_vat(self.company_id.vat)
        result['TED']['DD']['TD'] = self.sii_document_class_id.sii_code
        result['TED']['DD']['F']  = folio
        result['TED']['DD']['FE'] = self.date_invoice
        if not self.partner_id.vat:
            raise UserError(_("Fill Partner VAT"))
        result['TED']['DD']['RR'] = cm.format_vat(self.partner_id.vat)
        result['TED']['DD']['RSR'] = self.normalize_string(
            self.partner_id.name, 40)
        result['TED']['DD']['MNT'] = int(round(self.amount_total))
        if no_product:
            result['TED']['DD']['MNT'] = 0
        for line in self.invoice_line_ids:
            result['TED']['DD']['IT1'] = self.normalize_string(
                line.product_id.name, 40)
            if line.product_id.default_code:
                result['TED']['DD']['IT1'] = self.normalize_string(
                    line.product_id.name.replace(
                        '['+line.product_id.default_code+'] ', ''), 40)
            break

        resultcaf = self.get_caf_file()
        # raise UserError('result caf: {}'.format(resultcaf))
        result['TED']['DD']['CAF'] = resultcaf['AUTORIZACION']['CAF']
        dte = result['TED']['DD']
        dicttoxml.set_debug(False)
        ddxml = '<DD>'+dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).replace(
            '<key name="@version">1.0</key>', '', 1).replace(
            '><key name="@version">1.0</key>', ' version="1.0">', 1).replace(
            '><key name="@algoritmo">SHA1withRSA</key>',
            ' algoritmo="SHA1withRSA">').replace(
            '<key name="#text">', '').replace(
            '</key>', '').replace('<CAF>', '<CAF version="1.0">')+'</DD>'
        ddxml = self.convert_encoding(ddxml, 'utf-8')
        keypriv = (resultcaf['AUTORIZACION']['RSASK']).encode(
            'latin-1').replace('\t', '')
        keypub = (resultcaf['AUTORIZACION']['RSAPUBK']).encode(
            'latin-1').replace('\t', '')
        #####
        ## antes de firmar, formatear
        root = etree.XML(ddxml)
        ##
        # formateo sin remover indents
        ddxml = etree.tostring(root)
        timestamp = self.time_stamp()
        ddxml = ddxml.replace('2014-04-24T12:02:20', timestamp)
        frmt = si.signmessage(ddxml, keypriv, keypub)['firma']
        ted = (
            '''<TED version="1.0">{}<FRMT algoritmo="SHA1withRSA">{}\
</FRMT></TED>''').format(ddxml, frmt)
        root = etree.XML(ted)
        self.sii_barcode = ted
        if ted:
            barcodefile = StringIO()
            image = si.pdf417bc(ted)
            image.save(barcodefile, 'PNG')
            data = barcodefile.getvalue()
            self.sii_barcode_img = base64.b64encode(data)
        ted += '<TmstFirma>{}</TmstFirma>'.format(timestamp)
        return ted

    @api.multi
    def wizard_upload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sii.dte.upload_xml.wizard',
            'src_model': 'account.invoice',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'tag': 'action_upload_xml_wizard'}

    @api.multi
    def wizard_validar(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sii.dte.validar.wizard',
            'src_model': 'account.invoice',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'tag': 'action_validar_wizard'}

    @api.multi
    def invoice_print(self):
        self.ensure_one()
        self.sent = True
        if self.ticket:
            return self.env['report'].get_action(
                self, 'l10n_cl_dte.report_ticket')
        return self.env['report'].get_action(self, 'account.report_invoice')

    @api.multi
    def print_cedible(self):
        """ Print Cedible
        """
        return self.env['report'].get_action(
            self, 'l10n_cl_dte.invoice_cedible')

    @api.multi
    def get_total_discount(self):
        total_discount = 0
        for l in self.invoice_line_ids:
            total_discount += (
                ((l.discount or 0.00) / 100) * l.price_unit * l.quantity)
        _logger.info(total_discount)
        return self.currency_id.round(total_discount)
