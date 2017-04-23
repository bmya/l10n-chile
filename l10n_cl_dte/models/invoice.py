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
from lxml.etree import Element, SubElement
import pytz
import collections
import urllib3
import xmltodict
import dicttoxml
import base64
import M2Crypto
from elaphe import barcode
import hashlib
import textwrap
import cchardet
from SOAPpy import SOAPProxy
from signxml import XMLSigner, XMLVerifier, methods
from bs4 import BeautifulSoup as bs
try:
    urllib3.disable_warnings()
except:
    pass
_logger = logging.getLogger(__name__)
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
import requests

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
    'SII': 'https://palena.sii.cl/DTEWS/', }
BC = '''-----BEGIN CERTIFICATE-----\n'''
EC = '''\n-----END CERTIFICATE-----\n'''
try:
    pool = urllib3.PoolManager()
except:
    pass
import os
connection_status = {
    '0': 'Upload OK',
    '1': 'El remitente no tiene permiso para enviar',
    '2': 'Error en tamaño del archivo (muy grande o muy chico)',
    '3': 'Archivo cortado (tamaño <> al parámetro size)',
    '5': 'No está autenticado',
    '6': 'Empresa no autorizada a enviar archivos',
    '7': 'Esquema Invalido',
    '8': 'Firma del Documento',
    '9': 'Sistema Bloqueado',
    'Otro': 'Error Interno.', }
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace(
    '/models', '/static/xsd/')
host = 'https://libredte.cl/api'
api_emitir = host + '/dte/documentos/emitir'
api_generar = host + '/dte/documentos/generar'
api_gen_pdf = host + '/dte/documentos/generar_pdf'
api_get_xml = host + '/dte/dte_emitidos/xml/{0}/{1}/{2}'
api_upd_status = host + '/dte/dte_emitidos/actualizar_estado/'
no_product = False


class Signer(XMLSigner):
    def __init__(self):
        super(Signer, self).__init__(
            method=methods.detached,
            signature_algorithm='rsa-sha1',
            digest_algorithm='sha1',
            c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')

    def key_value_serialization_is_required(self, cert_chain):
        return True


class Invoice(models.Model):
    """
    Extension of data model to contain global parameters needed
    for all electronic invoice integration.
    @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    @version: 2016-06-11
    """
    _inherit = "account.invoice"

    # metodos comunes
    @staticmethod
    def safe_variable(var, key):
        try:
            msg = normalize_tags[key][1]
            len = normalize_tags[key][0]
            var = var[:len]
        except:
            msg = u'variable'
        if not var:
            raise UserError(
                u'{} no está configurada.'.format(msg))
        return var

    @staticmethod
    def format_vat(value):
        if not value or value == '' or value == 0:
            value = "CL666666666"
        else:
            value = (value[:10] + '-' + value[10:]).replace(
                'CL0', '').replace('CL', '')
        return value

    @staticmethod
    def analyze_sii_result(sii_result, sii_message, sii_receipt):
        _logger.info(
            'analizando sii result: {} - message: {} - receipt: {}'.format(
                sii_result, sii_message, sii_receipt))
        if not sii_result or not sii_message or not sii_receipt:
            return sii_result
        soup_message = bs(sii_message, 'xml')
        soup_receipt = bs(sii_receipt, 'xml')
        _logger.info(soup_message)
        _logger.info(soup_receipt)
        if soup_message.ESTADO.text == '2':
            raise UserError(
                'Error code: 2: {}'.format(soup_message.GLOSA_ERR.text))
        if soup_message.ESTADO.text in ['SOK', 'CRT', 'PDR', 'FOK', '-11']:
            return 'Proceso'
        elif soup_message.ESTADO.text in ['RCH', 'RFR', 'RSC', 'RCT']:
            return 'Rechazado'
        elif soup_message.ESTADO.text in ['RLV']:
            return 'Reparo'
        elif soup_message.ESTADO.text in ['EPR', 'DNK']:
            if soup_receipt.ACEPTADOS.text == soup_receipt.INFORMADOS.text:
                return 'Aceptado'
            if soup_receipt.REPAROS.text >= '1':
                return 'Reparo'
            if soup_receipt.RECHAZADOS.text >= '1':
                return 'Rechazado'
        return sii_result

    @staticmethod
    def _calc_discount_vat(discount, sii_code):
        """
        Función provisoria para calcular el descuento:
        TODO
        @author: Daniel Blanco
        @version: 2016-12-30
        :return:
        """
        return discount

    @staticmethod
    def safe_date(date):
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        return date

    def normalize_string(
            self, var, key, control='truncate'):
        _logger.info('var: {}, key: {}, control: {}')
        if isinstance(key, (int, long, float, complex)):
            size = key
            control = 'truncate'
        else:
            size = normalize_tags[key][0]
        if self.company_id.dte_service_provider in ['LIBREDTE']:
            var = self.char_replace(var)
            # var = unicodedata.normalize(
            # 'NFKD', var).encode('ascii', 'ignore')
        if control == 'truncate':
            var = var[:size]
        elif control == 'safe':
            self.safe_variable(var, key)
        return var

    # metodos de libredte
    @staticmethod
    def remove_plurals_node(dte):
        dte1 = collections.OrderedDict()
        for k, v in dte.items():
            if k in pluralizeds:
                k = k[:-1]
                vn = []
                for v1 in v:
                    vn.append(v1[k])
                    v = vn
            else:
                k, v = k, v
            dte1[k] = v
        return dte1

    # metodos de sii
    @api.model
    def check_if_not_sent(self, ids, model, job):
        queue_obj = self.env['sii.cola_envio']
        item_ids = queue_obj.search(
            [('doc_ids', 'like', ids), ('model', '=', model),
             ('tipo_trabajo', '=', job)])
        return len(item_ids) <= 0

    @staticmethod
    def remove_plurals_xml(xml):
        for k in pluralizeds:
            print k
            xml = xml.replace('<%s>' % k, '').replace('</%s>' % k, '')
        return xml

    @staticmethod
    def create_template_doc(doc):
        """
        Creacion de plantilla xml para envolver el DTE
        Previo a realizar su firma (1)
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-01
        """
        xml = '''<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
    {}</DTE>'''.format(doc)
        return xml

    @staticmethod
    def split_cert(cert):
        certf, j = '', 0
        for i in range(0, 29):
            certf += cert[76 * i:76 * (i + 1)] + '\n'
        return certf

    @staticmethod
    def create_template_envelope(
            RutEmisor, RutReceptor, FchResol, NroResol, TmstFirmaEnv, EnvioDTE,
            signature_d, SubTotDTE):
        """
        Funcion que permite crear una plantilla para el EnvioDTE
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-06-01
        :param RutEmisor:
        :param RutReceptor:
        :param FchResol:
        :param NroResol:
        :param TmstFirmaEnv:
        :param EnvioDTE:
        :param signature_d:
        :param SubTotDTE:
        :return:
        """
        xml = '''<SetDTE ID="BMyA_Odoo_SetDoc">
<Caratula version="1.0">
<RutEmisor>{0}</RutEmisor>
<RutEnvia>{1}</RutEnvia>
<RutReceptor>{2}</RutReceptor>
<FchResol>{3}</FchResol>
<NroResol>{4}</NroResol>
<TmstFirmaEnv>{5}</TmstFirmaEnv>
{6}</Caratula>{7}
</SetDTE>'''.format(RutEmisor, signature_d['subject_serial_number'],
                    RutReceptor, FchResol, NroResol, TmstFirmaEnv, SubTotDTE,
                    EnvioDTE)
        return xml

    @staticmethod
    def get_seed(company_id):
        """
        Funcion usada en autenticacion en SII
        Obtencion de la semilla desde el SII.
        Basada en función de ejemplo mostrada en el sitio edreams.cl
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2015-04-01
        """
        try:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
        url = server_url[
                  company_id.dte_service_provider] + 'CrSeed.jws?WSDL'
        ns = 'urn:' + server_url[
            company_id.dte_service_provider] + 'CrSeed.jws'
        _server = SOAPProxy(url, ns)
        root = etree.fromstring(_server.getSeed())
        semilla = root[0][0].text
        return semilla

    @staticmethod
    def create_template_seed(seed):
        """
        Funcion usada en autenticacion en SII
        Creacion de plantilla xml para realizar el envio del token
        Previo a realizar su firma
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-06-01
        """
        xml = u'''<getToken>
<item>
<Semilla>{}</Semilla>
</item>
</getToken>
'''.format(seed)
        return xml

    @staticmethod
    def create_template_env(doc, typedoc='DTE'):
        """
        Funcion usada en autenticacion en SII
        Creacion de plantilla xml para envolver el Envio de DTEs
        Previo a realizar su firma (2da)
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-06-01
        """
        xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<Envio{1} xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte Envio{1}_v10.xsd" \
version="1.0">
{0}
</EnvioDTE>'''.format(doc, typedoc)
        return xml

    @staticmethod
    def create_template_doc1(doc, sign):
        """
        Funcion usada en autenticacion en SII
        Insercion del nodo de firma (1ra) dentro del DTE
        Una vez firmado.
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-06-01
        """
        xml = doc.replace('</DTE>', '') + sign + '</DTE>'
        return xml

    @staticmethod
    def create_template_env1(doc, sign):
        """
        Funcion usada en autenticacion en SII
        Insercion del nodo de firma (2da) dentro del DTE
        Una vez firmado.
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-06-01
        """
        xml = doc.replace('</EnvioDTE>', '') + sign + '</EnvioDTE>'
        return xml

    @staticmethod
    def append_sign_recep(doc, sign):
        xml = doc.replace('</Recibo>', '') + sign + '</Recibo>'
        return xml

    @staticmethod
    def append_sign_env_book(doc, sign):
        xml = doc.replace(
            '</LibroCompraVenta>', '') + sign + '</LibroCompraVenta>'
        return xml

    @staticmethod
    def append_sign_env_recep(doc, sign):
        xml = doc.replace('</EnvioRecibos>', '') + sign + '</EnvioRecibos>'
        return xml

    @staticmethod
    def append_sign_env_resp(doc, sign):
        xml = doc.replace('</RespuestaDTE>', '') + sign + '</RespuestaDTE>'
        return xml

    @staticmethod
    def append_sign_env_bol(doc, sign):
        xml = doc.replace('</EnvioBOLETA>', '') + sign + '</EnvioBOLETA>'
        return xml

    @staticmethod
    def sign_seed(message, privkey, cert):
        """
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-01
        """
        _logger.info('SIGNING WITH SIGN_SEED ##### ------ #####')
        doc = etree.fromstring(message)
        # signed_node = Signer.sign(
        #    doc, key=privkey.encode('ascii'), cert=cert, key_info=None)
        signed_node = XMLSigner(
            method=methods.enveloped, signature_algorithm=u'rsa-sha1',
            digest_algorithm=u'sha1').sign(
            doc, key=privkey.encode('ascii'), passphrase=None, cert=cert,
            key_name=None, key_info=None, id_attribute=None)
        msg = etree.tostring(
            signed_node, pretty_print=True).replace('ds:', '')
        _logger.info('message: {}'.format(msg))
        return msg

    @staticmethod
    def get_token(seed_file, company_id):
        """
        Funcion usada en autenticacion en SII
        Obtencion del token a partir del envio de la semilla firmada
        Basada en función de ejemplo mostrada en el sitio edreams.cl
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-01
        """
        url = server_url[
                  company_id.dte_service_provider] + 'GetTokenFromSeed.jws?WSDL'
        ns = 'urn:' + server_url[
            company_id.dte_service_provider] + 'GetTokenFromSeed.jws'
        _server = SOAPProxy(url, ns)
        tree = etree.fromstring(seed_file)
        ss = etree.tostring(tree, pretty_print=True, encoding='iso-8859-1')
        respuesta = etree.fromstring(_server.getToken(ss))
        token = respuesta[0][0].text
        return token

    @staticmethod
    def long_to_bytes(n, blocksize=0):
        """long_to_bytes(n:long, blocksize:int) : string
        Convert a long integer to a byte string.
        If optional blocksize is given and greater than zero, pad the front of
        the byte string with binary zeros so that the length is a multiple of
        blocksize.
        """
        # after much testing, this algorithm was deemed to be the fastest
        s = b''
        n = long(n)
        # noqa
        import struct
        pack = struct.pack
        while n > 0:
            s = pack(b'>I', n & 0xffffffff) + s
            n = n >> 32
        # strip off leading zeros
        for i in range(len(s)):
            if s[i] != b'\000'[0]:
                break
        else:
            # only happens when n == 0
            s = b'\000'
            i = 0
        s = s[i:]
        # add back some pad bytes.  this could be done more efficiently
        # w.r.t. the
        # de-padding being done above, but sigh...
        if blocksize > 0 and len(s) % blocksize:
            s = (blocksize - len(s) % blocksize) * b'\000' + s
        return s

    @staticmethod
    def ensure_str(x, encoding="utf-8", none_ok=False):
        if none_ok is True and x is None:
            return x
        if not isinstance(x, str):
            x = x.decode(encoding)
        return x

    @staticmethod
    def pdf417bc(ted):
        """
        Funcion creacion de imagen pdf417 basada en biblioteca elaphe
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-05-01
        """
        bc = barcode(
            'pdf417',
            ted,
            options=dict(
                compact=False,
                eclevel=5,
                columns=13,
                rowmult=2,
                rows=3
            ),
            margin=20,
            scale=1
        )
        return bc

    @staticmethod
    def digest(data):
        """
        Funcion usada en SII
        para firma del timbre (dio errores de firma para el resto de los doc)
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2015-03-01
        """
        sha1 = hashlib.new('sha1', data)
        return sha1.digest()

    @staticmethod
    def xml_validator(some_xml_string, validacion='doc'):
        """
        Funcion para validar los xml generados contra el esquema que le
        corresponda segun el tipo de documento.
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-01. Se agregó validación para boletas
        Modificada por Daniel Santibañez 2016-08-01
        """
        if validacion == 'bol':
            return True
        validacion_type = {
            'doc': 'DTE_v10.xsd',
            'env': 'EnvioDTE_v10.xsd',
            'env_boleta': 'EnvioBOLETA_v11.xsd',
            'recep': 'Recibos_v10.xsd',
            'env_recep': 'EnvioRecibos_v10.xsd',
            'env_resp': 'RespuestaEnvioDTE_v10.xsd',
            'sig': 'xmldsignature_v10.xsd',
            'book': 'LibroCV_v10.xsd',
        }
        xsd_file = xsdpath + validacion_type[validacion]
        try:
            xmlschema_doc = etree.parse(xsd_file)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            xml_doc = etree.fromstring(some_xml_string)
            result = xmlschema.validate(xml_doc)
            if not result:
                xmlschema.assert_(xml_doc)
            return result
        except AssertionError as e:
            _logger.info(etree.tostring(xml_doc))
            raise UserError(
                _('XML Malformed Error: {} - Validation: {}').format(
                    e.args, validacion))

    def send_xml_file(
            self, envio_dte=None, file_name="envio", company_id=False,
            sii_result='NoEnviado', doc_ids=''):
        if not company_id.dte_service_provider:
            raise UserError(_("Not Service provider selected!"))
        # try:
        signature_d = self.get_digital_signature_pem(
            company_id)
        seed = self.get_seed(company_id)
        template_string = self.create_template_seed(seed)
        seed_firmado = self.sign_seed(
            template_string, signature_d['priv_key'],
            signature_d['cert'])
        token = self.get_token(seed_firmado, company_id)
        # raise UserError(token)
        # except:
        #    _logger.info('error')
        #    return

        # better explicit than implicit...
        if company_id.dte_service_provider == 'SIIHOMO':
            url = 'https://maullin.sii.cl'
        else:
            url = 'https://palena.sii.cl'
        post = '/cgi_dte/UPL/DTEUpload'
        headers = {
            'Accept': 'image/gif, image/x-xbitmap, image/jpeg, \
image/pjpeg, application/vnd.ms-powerpoint, application/ms-excel, \
application/msword, */*',
            'Accept-Language': 'es-cl',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/4.0 (compatible; PROG 1.0; Windows NT 5.0; \
YComp 5.0.2.4)',
            'Referer': '{}'.format(company_id.website),
            'Connection': 'Keep-Alive',
            'Cache-Control': 'no-cache',
            'Cookie': 'TOKEN={}'.format(token), }
        params = collections.OrderedDict()
        params['rutSender'] = signature_d['subject_serial_number'][:8]
        params['dvSender'] = signature_d['subject_serial_number'][-1]
        params['rutCompany'] = company_id.vat[2:-1]
        params['dvCompany'] = company_id.vat[-1]
        params['archivo'] = (file_name, envio_dte, "text/xml")
        multi = urllib3.filepost.encode_multipart_formdata(params)
        headers.update({'Content-Length': '{}'.format(len(multi[0]))})
        response = pool.request_encode_body('POST', url + post, params,
                                            headers)
        retorno = {
            'sii_xml_response': response.data,
            'sii_result': 'NoEnviado',
            'sii_send_ident': '', }
        if response.status != 200:
            return retorno
        respuesta_dict = xmltodict.parse(response.data)
        if respuesta_dict['RECEPCIONDTE']['STATUS'] != '0':
            _logger.info(
                connection_status[respuesta_dict['RECEPCIONDTE']['STATUS']])
        else:
            retorno.update(
                {'sii_result': 'Enviado',
                 'sii_send_ident': respuesta_dict['RECEPCIONDTE'][
                     'TRACKID']})
        return retorno

    def sign_full_xml(self, message, privkey, cert, uri, type='doc'):
        doc = etree.fromstring(message)
        string = etree.tostring(doc[0])
        # raise UserError('string sign: {}'.format(message))
        mess = etree.tostring(etree.fromstring(string), method="c14n")
        digest = base64.b64encode(self.digest(mess))
        reference_uri = '#' + uri
        signed_info = Element("SignedInfo")
        c14n_method = SubElement(
            signed_info, "CanonicalizationMethod",
            Algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        sign_method = SubElement(
            signed_info, "SignatureMethod",
            Algorithm='http://www.w3.org/2000/09/xmldsig#rsa-sha1')
        reference = SubElement(signed_info, "Reference", URI=reference_uri)
        transforms = SubElement(reference, "Transforms")
        SubElement(
            transforms, "Transform",
            Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        digest_method = SubElement(
            reference, "DigestMethod",
            Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
        digest_value = SubElement(reference, "DigestValue")
        digest_value.text = digest
        signed_info_c14n = etree.tostring(
            signed_info, method="c14n", exclusive=False,
            with_comments=False, inclusive_ns_prefixes=None)
        if type in ['doc', 'recep']:
            att = 'xmlns="http://www.w3.org/2000/09/xmldsig#"'
        else:
            att = 'xmlns="http://www.w3.org/2000/09/xmldsig#" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        # @TODO Find better way to add xmlns:xsi attrib
        signed_info_c14n = signed_info_c14n.replace(
            "<SignedInfo>", "<SignedInfo " + att + ">")
        sig_root = Element(
            "Signature",
            attrib={'xmlns': 'http://www.w3.org/2000/09/xmldsig#'})
        sig_root.append(etree.fromstring(signed_info_c14n))
        signature_value = SubElement(sig_root, "SignatureValue")
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.serialization \
            import load_pem_private_key
        import OpenSSL
        from OpenSSL.crypto import *
        type_ = FILETYPE_PEM
        key = OpenSSL.crypto.load_privatekey(type_, privkey.encode('ascii'))
        signature = OpenSSL.crypto.sign(key, signed_info_c14n, 'sha1')
        signature_value.text = textwrap.fill(base64.b64encode(signature),
                                             64)
        key_info = SubElement(sig_root, "KeyInfo")
        key_value = SubElement(key_info, "KeyValue")
        rsa_key_value = SubElement(key_value, "RSAKeyValue")
        modulus = SubElement(rsa_key_value, "Modulus")
        key = load_pem_private_key(
            privkey.encode('ascii'), password=None,
            backend=default_backend())
        modulus.text = textwrap.fill(
            base64.b64encode(
                self.long_to_bytes(key.public_key().public_numbers().n)),
            64)
        exponent = SubElement(rsa_key_value, "Exponent")
        exponent.text = self.ensure_str(
            base64.b64encode(self.long_to_bytes(
                key.public_key().public_numbers().e)))
        x509_data = SubElement(key_info, "X509Data")
        x509_certificate = SubElement(x509_data, "X509Certificate")
        x509_certificate.text = '\n' + textwrap.fill(cert, 64)
        msg = etree.tostring(sig_root)
        msg = msg if self.xml_validator(msg, 'sig') else ''
        if type in ['doc', 'bol']:
            fulldoc = self.create_template_doc1(message, msg)
        if type == 'env':
            fulldoc = self.create_template_env1(message, msg)
        if type == 'recep':
            fulldoc = self.append_sign_recep(message, msg)
        if type == 'env_recep':
            fulldoc = self.append_sign_env_recep(message, msg)
        if type == 'env_resp':
            fulldoc = self.append_sign_env_resp(message, msg)
        if type == 'env_boleta':
            fulldoc = self.append_sign_env_bol(message, msg)
        if type == 'book':
            fulldoc = self.append_sign_env_book(message, msg)
        fulldoc = fulldoc if self.xml_validator(fulldoc, type) else ''
        return fulldoc

    def signrsa(self, MESSAGE, KEY, digst=''):
        """
        Funcion usada en SII
        para firma del timbre (dio errores de firma para el resto de los doc)
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2015-03-01
        """
        KEY = KEY.encode('ascii')
        rsa = M2Crypto.EVP.load_key_string(KEY)
        rsa.reset_context(md='sha1')
        rsa_m = rsa.get_rsa()
        rsa.sign_init()
        rsa.sign_update(MESSAGE)
        FRMT = base64.b64encode(rsa.sign_final())
        if digst == '':
            return {
                'firma': FRMT, 'modulus': base64.b64encode(rsa_m.n),
                'exponent': base64.b64eDigesncode(rsa_m.e)}
        else:
            return {
                'firma': FRMT, 'modulus': base64.b64encode(rsa_m.n),
                'exponent': base64.b64encode(rsa_m.e),
                'digest': base64.b64encode(self.digest(MESSAGE))}

    def signmessage(self, MESSAGE, KEY, pubk='', digst=''):
        """
        Funcion usada en SII
        para firma del timbre (dio errores de firma para el resto de los doc)
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2015-03-01
        """
        rsa = M2Crypto.EVP.load_key_string(KEY)
        rsa.reset_context(md='sha1')
        rsa_m = rsa.get_rsa()
        rsa.sign_init()
        rsa.sign_update(MESSAGE)
        FRMT = base64.b64encode(rsa.sign_final())
        if digst == '':
            return {
                'firma': FRMT, 'modulus': base64.b64encode(rsa_m.n),
                'exponent': base64.b64encode(rsa_m.e)}
        else:
            return {
                'firma': FRMT, 'modulus': base64.b64encode(rsa_m.n),
                'exponent': base64.b64encode(rsa_m.e),
                'digest': base64.b64encode(self.digest(MESSAGE))}

    def clean_relationships(self, model='invoice.reference'):
        """
        Limpia relaciones
        todo: retomar un modelo de datos de relaciones de documentos
        más acorde, en lugar de account.invoice.referencias.
        #
        @author: Daniel Blanco daniel[at]blancomartin.cl
        @version: 2016-09-29
        :return:
        """
        invoice_id = self.id
        ref_obj = self.env[model]
        ref_obj.search([('invoice_id', '=', invoice_id)]).unlink()

    # fin metodos independientes

    @staticmethod
    def char_replace(text):
        """
        Funcion para reemplazar caracteres especiales
        Esta funcion sirve para salvar bug en libreDTE con los recortes de
        giros que están codificados en utf8 (cuando trunca, trunca la
        codificacion)
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-07-31
        """
        special_chars = [
            [u'á', 'a'],
            [u'é', 'e'],
            [u'í', 'i'],
            [u'ó', 'o'],
            [u'ú', 'u'],
            [u'ñ', 'n'],
            [u'Á', 'A'],
            [u'É', 'E'],
            [u'Í', 'I'],
            [u'Ó', 'O'],
            [u'Ú', 'U'],
            [u'Ñ', 'N']]
        for char in special_chars:
            try:
                text = text.replace(char[0], char[1])
            except:
                pass
        return text

    def enviar_ldte(self, dte, headers):
        """
        Función para enviar el dte a libreDTE
        @author: Daniel Blanco
        @version: 2017-02-11
        :param headers:
        :param dte:
        :return:
        Notar que esta llama al bring_xml_ldte
        """
        dte['Encabezado']['Emisor'] = self.remove_plurals_node(
            dte['Encabezado']['Emisor'])
        dte = self.remove_plurals_node(dte)
        dte['Encabezado']['Emisor']['Acteco'] = dte[
            'Encabezado']['Emisor']['Acteco'][0]
        _logger.info('despues de remover plurales {}'.format(json.dumps(dte)))
        # raise UserError('enviar-ldte')
        response_emitir = pool.urlopen(
            'POST', api_emitir, headers=headers, body=json.dumps(dte))
        if response_emitir.status != 200:
            raise UserError(
                'Error en conexión al emitir: {}, {}'.format(
                    response_emitir.status, response_emitir.data))
        _logger.info('response_emitir: {}'.format(
            response_emitir.data))
        _logger.info('response_emitir respuesta satisfactoria')
        try:
            self.sii_xml_response = response_emitir.data
            _logger.info('response_xml: {}'.format(
                response_emitir.data))
            _logger.info('try positivo')
        except:
            _logger.warning(
                'no pudo guardar la respuesta al ws de emision')
            _logger.info('try negativo')
        '''
        {"emisor": ----, "receptor": -, "dte": --,
         "codigo": "-----"}
        '''
        response_emitir_data = response_emitir.data
        response_j = self.bring_xml_ldte(response_emitir_data, headers=headers)
        _logger.info('vino de bring_xml_dte')
        _logger.info('response_j')
        _logger.info(response_j)
        return response_j

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
    def time_stamp(format='%Y-%m-%dT%H:%M:%S'):
        tz = pytz.timezone('America/Santiago')
        return datetime.now(tz).strftime(format)

    @staticmethod
    def convert_encoding(data, new_coding='UTF-8'):
        """
        Funcion auxiliar para conversion de codificacion de strings
        proyecto experimentos_dte
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2014-12-01
        """
        try:
            encoding = cchardet.detect(data)['encoding']
            _logger.info('ENCODING #################')
            _logger.info(encoding)
        except:
            encoding = 'ascii'
        if new_coding.upper() != encoding.upper():
            try:
                data = data.decode(encoding=encoding, errors='ignore')
            except:
                try:
                    data = data.decode(encoding='UTF-8', errors='ignore')
                except:
                    try:
                        data = data.decode(
                            encoding='ISO-8859-9', errors='replace')
                    except:
                        pass
            data = data.encode(encoding=new_coding, errors='ignore')
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

    def get_digital_signature_pem(self, comp_id):
        obj = user = False
        # if 'responsable_envio' in self and self._ids:
        #    obj = user = self[0].responsable_envio
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
            'rut_envia': obj.subject_serial_number, }
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

    def get_folio(self):
        """
        Funcion para descargar el folio tomando el valor desde la secuencia
        correspondiente al tipo de documento.
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-05-01
        """
        if self.state in ['draft']:
            return int(self.next_invoice_number)
        else:
            return self.get_folio_current()

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

    def is_doc_type_b(self):
        """
        Funcion para encontrar documentos tipo "boleta"
        En lugar de poner una lista con codigos del sii, pongo un tipo basado
        en parametrización hecha previamente (boletas = documentos tipo "b"
        y tipo "m" según definición histórica en l10n_cl_invoice, ya que el
        modelo letter lo que hace es parametrizar los comportamientos de
        los documentos
        :return:
        """
        # return self.sii_document_class_id.sii_code in [
            # 35, 38, 39, 41, 70, 71]
        return self.sii_document_class_id.document_letter_id.name in ['B', 'M']


    def _giros_sender(self):
        giros_sender = []
        for turn in self.company_id.company_activities_ids:
            giros_sender.extend([{'Acteco': turn.code}])
            # giros_sender.extend([turn.code])
        return giros_sender

    def _id_doc(self, tax_include=False, MntExe=0):
        IdDoc = collections.OrderedDict()
        IdDoc['TipoDTE'] = self.sii_document_class_id.sii_code
        IdDoc['Folio'] = self.get_folio()
        IdDoc['FchEmis'] = self.safe_date(self.date_invoice)
        self.date_invoice = self.safe_date(self.date_invoice)
        if self.is_doc_type_b():
            IdDoc['IndServicio'] = 3
            # TODO agregar las otras opciones a la fichade producto servicio
        if self.ticket:
            IdDoc['TpoImpresion'] = "T"
        # if self.tipo_servicio:
        #    Encabezado['IdDoc']['IndServicio'] = 1,2,3,4
        # todo: forma de pago y fecha de vencimiento - opcional
        if tax_include and MntExe == 0 and not self.is_doc_type_b():
            IdDoc['MntBruto'] = 1
        if not self.is_doc_type_b():
            IdDoc['FmaPago'] = self.forma_pago or 1
        if not tax_include and self.is_doc_type_b():
            IdDoc['IndMntNeto'] = 2
        #if self.is_doc_type_b():
            #Servicios periódicos
        #    IdDoc['PeriodoDesde'] =
        #    IdDoc['PeriodoHasta'] =
        if not self.is_doc_type_b():
            IdDoc['FchVenc'] = self.date_due or datetime.strftime(
                datetime.now(), '%Y-%m-%d')
        return IdDoc

    def _sender(self):
        emisor= collections.OrderedDict()
        emisor['RUTEmisor'] = self.format_vat(self.company_id.vat)
        if self.is_doc_type_b():
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
            emisor['Actecos'] = self._giros_sender()
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
        if not self.partner_id.vat and not self.is_doc_type_b():
            raise UserError("Debe Ingresar RUT Receptor")
        # if self.is_doc_type_b():
        #     receptor['CdgIntRecep']
        receptor['RUTRecep'] = self.format_vat(self.partner_id.vat)
        receptor['RznSocRecep'] = self.normalize_string(
            self.partner_id.name, 'RznSocRecep', 'safe')
        if not self.is_doc_type_b():
            # if not self.activity_description:
            #    raise UserError(_('Seleccione giro del partner.'))
            # receptor['GiroRecep'] = self.normalize_string(
            #     self.activity_description.name, 'GiroRecep', 'safe')
            receptor['GiroRecep'] = self.normalize_string(
                self.invoice_turn.name, 'GiroRecep', 'safe')
        if self.partner_id.phone:
            receptor['Contacto'] = self.normalize_string(
                self.partner_id.phone, 'Contacto', 'truncate')
        if self.partner_id.dte_email and not self.is_doc_type_b():
            receptor['CorreoRecep'] = self.partner_id.dte_email
        receptor['DirRecep'] = self.normalize_string('{} {}'.format(
            self.partner_id.street or '',
            self.partner_id.street2 or ''), 'DirRecep', 'safe')
        receptor['CmnaRecep'] = self.normalize_string(
            self.partner_id.city_id.name, 'CmnaRecep', 'safe')
        receptor['CiudadRecep'] = self.normalize_string(
            self.partner_id.city, 'CiudadRecep', 'safe')
        return receptor

    def _totals(self, MntExe=0, no_product=False, tax_include=False):
        totals = collections.OrderedDict()
        if self.sii_document_class_id.sii_code == 34 or (
                self.referencias and self.referencias[0].
                sii_referencia_TpoDocRef.sii_code == '34'):
            self.mnt_exe = totals['MntExe'] = int(round(self.amount_total, 0))
            if no_product:
                self.mnt_exe = totals['MntExe'] = 0
        elif self.amount_untaxed and self.amount_untaxed != 0:
            if not self.is_doc_type_b() or not tax_include:
                IVA = False
                for t in self.tax_line_ids:
                    if t.tax_id.sii_code in [14, 15]:
                        IVA = t
                if IVA and IVA.base > 0:
                    totals['MntNeto'] = int(round((IVA.base), 0))
            if MntExe > 0:
                self.mnt_exe = totals['MntExe'] = int(round(MntExe))
            if not self.is_doc_type_b() or not tax_include:
                if IVA:
                    if not self.is_doc_type_b():
                        totals['TasaIVA'] = round(IVA.tax_id.amount,2)
                    totals['IVA'] = int(round(IVA.amount, 0))
                if no_product:
                    totals['MntNeto'] = 0
                    if not self.is_doc_type_b():
                        totals['TasaIVA'] = 0
                    totals['IVA'] = 0
            if IVA and IVA.tax_id.sii_code in [15]:
                totals['ImptoReten'] = collections.OrderedDict()
                totals['ImptoReten']['TpoImp'] = IVA.tax_id.sii_code
                totals['ImptoReten']['TasaImp'] = round(IVA.tax_id.amount,2)
                totals['ImptoReten']['MontoImp'] = int(round(IVA.amount))
        monto_total = int(round(self.amount_total, 0))
        if no_product:
            monto_total = 0
        totals['MntTotal'] = monto_total

        #totals['MontoNF']
        #totals['TotalPeriodo']
        #totals['SaldoAnterior']
        #totals['VlrPagar']
        return totals

    def _encabezado(self, MntExe=0, no_product=False, tax_include=False):
        encabezado = collections.OrderedDict()
        encabezado['IdDoc'] = self._id_doc(tax_include, MntExe)
        encabezado['Emisor'] = self._sender()
        encabezado['Receptor'] = self._receptor()
        if self.company_id.dte_service_provider not in ['LIBREDTE']:
            encabezado['Totales'] = self._totals(MntExe, no_product)
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
                #            if self.is_doc_type_b():
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

    def _dte(self, att_number=None):
        dte = collections.OrderedDict()
        invoice_lines = self._invoice_lines()
        dte['Encabezado'] = self._encabezado(
            invoice_lines['MntExe'], invoice_lines['no_product'],
            invoice_lines['tax_include'])
        lin_ref = 1
        ref_lines = []
        if self.company_id.dte_service_provider == 'SIIHOMO' and isinstance(
                att_number, unicode) and att_number != '' and \
                not self.is_doc_type_b():
            ref_line = collections.OrderedDict()
            ref_line['NroLinRef'] = lin_ref
            ref_line['TpoDocRef'] = "SET"
            ref_line['FolioRef'] = self.get_folio()
            ref_line['FchRef'] = datetime.strftime(datetime.now(),
                                                   '%Y-%m-%d')
            ref_line['RazonRef'] = "CASO " + att_number + "-" + str(
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
                if not self.is_doc_type_b():
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
                if self.is_doc_type_b():
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

    def _do_stamp(self, att_number=None):
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
        dte[(tpo_dte + ' ID')] = self._dte(att_number)
        xml = self._dte_to_xml(dte, tpo_dte)
        root = etree.XML(xml)
        xml_pret = etree.tostring(root, pretty_print=True).replace(
            '<' + tpo_dte + '_ID>', doc_id).replace(
            '</' + tpo_dte + '_ID>', '</' + tpo_dte + '>')
        xml_pret = self.remove_plurals_xml(xml_pret)
        envelope_efact = self.convert_encoding(xml_pret, 'ISO-8859-1')
        envelope_efact = self.create_template_doc(envelope_efact)
        _logger.info('envelope_efact: {}'.format(envelope_efact))
        type = 'bol' if self.is_doc_type_b() else 'doc'
        #    type = 'bol'
        einvoice = self.sign_full_xml(
            envelope_efact, signature_d['priv_key'],
            self.split_cert(certp), doc_id_number, type)
        # raise UserError('envelope_efact: {}'.format(envelope_efact))
        self.sii_xml_request = einvoice

    def _get_send_status(self, track_id, signature_d, token):
        url = server_url[
                  self.company_id.dte_service_provider] + 'QueryEstUp.jws?WSDL'
        ns = 'urn:' + server_url[
            self.company_id.dte_service_provider] + 'QueryEstUp.jws'
        _server = SOAPProxy(url, ns)
        rut = self.format_vat(self.company_id.vat)
        try:
            respuesta = _server.getEstUp(rut[:8], str(rut[-1]), track_id, token)
        except:
            raise UserError(u'Proceso: Obtener estado envío (get_send_status): \
No se pudo obtener una respuesta del servidor SII. RUT: {} DV: {} TrackID: \
{}, Token: {}'.format(rut[:8], str(rut[-1]), track_id, token))
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
                            'message': _(resp)}}
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
        receptor = self.format_vat(self.partner_id.vat)
        date_invoice = datetime.strptime(
            self.date_invoice, "%Y-%m-%d").strftime("%d%m%Y")
        rut = signature_d['subject_serial_number']
        try:
            respuesta = _server.getEstDte(
                rut[:8], str(rut[-1]), self.company_id.vat[2:-1],
                self.company_id.vat[-1], receptor[:8], receptor[2:-1],
                str(self.sii_document_class_id.sii_code),
                str(int(self.sii_document_number)), date_invoice,
                str(int(self.amount_total)), token)
            self.sii_message = respuesta
        except:
            _logger.info('Get Estado DTE: no se pudo obtener una respuesta \
del servidor. Se toma el varlor preexistente en el mensaje')
            # UserError('Get Estado DTE: no se pudo obtener una respuesta \
            # del servidor. intente nuevamente')
        if self.sii_message:
            # cambiar esto para hacerlo desde la funcion de "analyze"
            resp = xmltodict.parse(self.sii_message)
            try:
                if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == '2':
                    status = {
                        'warning': {
                            'title': _("Error code: 2"),
                            'message': _(
                                resp['SII:RESPUESTA']['SII:RESP_HDR']['GLOSA'])
                        }}
                    return status
                if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] in \
                        ['SOK', 'CRT', 'PDR', 'FOK', '-11']:
                    self.sii_result = 'Proceso'
                elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] in \
                        ['RCH', 'RFR', 'RSC', 'RCT']:
                    self.sii_result = 'Rechazado'
                elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] in ['RLV']:
                    self.sii_result = 'Reparo'
                elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == 'EPR':
                    if resp['SII:RESPUESTA']['SII:RESP_BODY'][
                    'ACEPTADOS'] == '1':
                        self.sii_result = 'Aceptado'
                    if resp['SII:RESPUESTA']['SII:RESP_BODY'][
                    'REPARO'] == '1':
                        self.sii_result = 'Reparo'
                    if resp['SII:RESPUESTA']['SII:RESP_BODY'][
                    'RECHAZADOS'] == '1':
                        self.sii_result = 'Rechazado'
            except:
                raise UserError('_get_dte_status: no se pudo obtener una \
respuesta satisfactoria por conexión ni de respuesta previa.')

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
            api_upd_status,
            str(self.sii_document_class_id.sii_code),
            str(folio),
            str(self.format_vat(self.company_id.vat)).replace(
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

    def save_xml_record(self, result, envio_dte, file_name):
        """
        Guarda el registro XML de las respuestas, pero no así el xml, el cual
        queda solamente con el DTE
        :param result:
        :param envio_dte:
        :param file_name:
        :return:
        """
        self.write(
            {'sii_xml_response': result['sii_xml_response'],
             'sii_send_ident': result['sii_send_ident'],
             'sii_result': result['sii_result'],
             # 'sii_xml_request': envio_dte,
             'sii_send_file_name': file_name, })

    # @send_recipient
    # def send_envelope_recipient(self):
    #     pass
    #
    # @send_sii
    # def send_envelope_sii(self):
    #     pass

    def save_xml_knowledge(self, result, envio_dte, file_name):
        attachment_obj = self.env['ir.attachment']
        _logger.info('Attachment')
        for inv in self:
            _logger.info(inv.sii_document_class_id.name)
            attachment_id = attachment_obj.create(
                {
                    'name': 'DTE_{}_{}.xml'.format(
                        inv.document_number, file_name).replace(' ', '_'),
                    'datas': base64.b64encode(envio_dte),
                    'datas_fname': 'DTE_{}-{}.xml'.format(
                        inv.document_number, file_name).replace(' ', '_'),
                    'res_model': inv._name,
                    'res_id': inv.id,
                    'type': 'binary', })
            _logger.info('Se ha generado factura en XML con el id {}'.format(
                attachment_id))

    def send_envelope_sii(
            self, RUTEmisor, resol_data, documentos, signature_d, SubTotDTE,
            file_name, company_id, certp):
        dtes = self.create_template_envelope(
            RUTEmisor, "60803000-K", resol_data['dte_resolution_date'],
            resol_data['dte_resolution_number'], self.time_stamp(), documentos,
            signature_d, SubTotDTE)
        env = 'env'
        envio_dte = self.create_template_env(dtes)
        envio_dte = self.sign_full_xml(
            envio_dte, signature_d['priv_key'], certp, 'BMyA_Odoo_SetDoc', env)
        result = self.send_xml_file(envio_dte, file_name, company_id)
        for inv in self:
            inv.save_xml_record(result, envio_dte, file_name)
        _logger.info('fin de preparacion y envio sii')
        return envio_dte

    def send_envelope_recipient(
            self, RUTEmisor, resol_data, documentos, signature_d, SubTotDTE,
            is_doc_type_b, file_name, company_id, certp):
        dtes = self.create_template_envelope(
            RUTEmisor, self.format_vat(self.partner_id.vat),
            resol_data['dte_resolution_date'],
            resol_data['dte_resolution_number'], self.time_stamp(), documentos,
            signature_d, SubTotDTE)
        env = 'env'
        if is_doc_type_b:
            envio_dte = self.create_template_env(dtes, 'BOLETA')
            env = 'env_boleta'
        else:
            envio_dte = self.create_template_env(dtes)
        envio_dte = self.sign_full_xml(
            envio_dte, signature_d['priv_key'], certp, 'BMyA_Odoo_SetDoc', env)
        result = self.send_xml_file(envio_dte, file_name, company_id)
        _logger.info('fin de preparacion y envio sii')
        for inv in self:
            inv.save_xml_knowledge(result, envio_dte, file_name)
            inv.get_pdf_docsonline(envio_dte)

    def get_pdf_docsonline(self, file_upload):
        host = 'https://www.documentosonline.cl'
        headers = {}
        headers['Accept'] = u'*/*'
        headers['Accept-Encoding'] = u'gzip, deflate, compress'
        headers['Connection'] = u'close'
        headers[
            'Content-Type'] = u'multipart/form-data; \
boundary=33b4531a79be4b278de5f5688fab7701'
        headers[
            'User-Agent'] = u'python-requests/2.2.1 CPython/2.7.6 Darwin/13.2.0'
        r = requests.post(host + '/dte/hgen/token',
                          files=dict(file_upload=file_upload))
        print r
        print r.text
        if r.status_code == 200:
            print json.loads(r.text)['token']
            self.docs_online_token = 'https://www.documentosonline.cl/\
dte/hgen/html/{}'.format(json.loads(r.text)['token'])
            headers['Connection'] = 'keep-alive'
            headers['Content-Type'] = 'application/json'
            data = {
                'params': json.loads(r.text)
            }
            print data
            r = requests.post(
                host + '/dte/jget',
                headers=headers,
                data=json.dumps(data))
            if r.status_code == 200:
                print r.json()
                invoice_pdf = json.loads(r.json()['result'])['pdf']
                attachment_name = self.get_attachment_name(
                    self, call_model=str(self._name))
                attachment_obj = self.env['ir.attachment']
                # raise UserError(self._name, self.id, self._context)
                record_id = self.get_object_record_id(
                    self, call_model=str(self._name))
                attachment_id = attachment_obj.create(
                    {
                        'name': 'DTE_' + attachment_name +
                                '-' + self.sii_document_number + '.pdf',
                        'datas': invoice_pdf,
                        'datas_fname': 'DTE_' + attachment_name +
                                       '-' + self.sii_document_number + '.pdf',
                        'res_model': self._name,
                        'res_id': record_id,
                        'type': 'binary'})
                _logger.info('attachment pdf')
                _logger.info(attachment_name)
                _logger.info(attachment_id)
                _logger.info(record_id)

    @api.multi
    def do_dte_send(self, att_number=None):
        """
        Este proceso sirve para manejar los envíos desde la cola de envíos
        :param att_number:
        :return:
        """
        dicttoxml.set_debug(False)
        DTEs = {}
        clases = {}
        company_id = False
        is_doc_type_b = False
        batch = 0
        # ACA ES DONDE SE DETERMINA EL ORDEN
        # DEBERÍA TENER ALGUNA MANERA DE ORDENAR EL SET DE DATOS QUE
        # VIENE EN SELF.
        for inv in self.with_context(lang='es_CL'):
            if not inv.sii_batch_number or inv.sii_batch_number == 0:
                batch += 1
                inv.sii_batch_number = batch
                # si viene una guía/nota regferenciando una factura,
                # que por numeración viene a continuación de la guia/nota,
                # será rechazada la guía porque debe estar declarada la
                # factura primero
            is_doc_type_b = inv.is_doc_type_b()
            # <- el boleta soy yo con estos nombres de funcion
            if inv.company_id.dte_service_provider in ['SII', 'SIIHOMO']:
                # raise UserError(inv.company_id.dte_service_provider)
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
                # otra culiadez... retimbrar de vuelta porque sí
                # si va a retimbrar para qué guardo antes el xml
                inv._do_stamp(att_number)
            elif inv.company_id.dte_service_provider == 'LIBREDTE':
                # sacar a la mierda del nuevo código
                _logger.info(
                    'desde do_dte_send, cola: {}'.format(inv._dte(att_number)))
            if not inv.sii_document_class_id.sii_code in clases:
                # en la  primera vuelta no hay nada en clases
                # aparentemente lo que quiere hacer, es ordenar por codigo de
                # documento, lo cual hace que se desordene el set de pruebas
                # esto va a haber que cambiarlo. está creando una lista de
                # documentos embebida en un diccionario de clases de documento
                clases[inv.sii_document_class_id.sii_code] = []
            clases[
                inv.sii_document_class_id.sii_code].extend(
                [{'id': inv.id,
                  'envio': inv.sii_xml_request,
                  'sii_batch_number': inv.sii_batch_number,
                  'sii_document_number': inv.sii_document_number}])
            # y aca copia las clases en DTEs... ya veremos en que se diferencia
            # clases de DTEs...
            DTEs.update(clases)
            if not company_id:
                company_id = inv.company_id
            elif company_id.id != inv.company_id.id:
                raise UserError('Está combinando compañías, no está permitido \
hacer eso en un envío')
            company_id = inv.company_id
            # @TODO hacer autoreconciliación <--- WHATAFUCK!!!! eso que carajo
            # tiene que ver, reconciliar los documentos con la factura
            # electronica?????? eso lo hace otro componente!
        file_name = ""
        dtes = {}  #  otro diccionario mas y van 3
        SubTotDTE = ''
        resol_data = self.get_resolution_data(company_id)
        signature_d = self.get_digital_signature(company_id)
        RUTEmisor = self.format_vat(company_id.vat)
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
<NroDTE>{}</NroDTE>
</SubTotDTE>
'''.format(NroDte)
        file_name += '.xml'
        documentos = ''
        for key in sorted(dtes.iterkeys()):
            documentos += '\n' + dtes[key]
        # raise UserError(documentos)
        if not is_doc_type_b:
            self.send_envelope_sii(
                RUTEmisor, resol_data, documentos, signature_d, SubTotDTE,
                file_name, company_id, certp)
        for inv in self:
            inv.sii_result = inv.analyze_sii_result(
                inv.sii_result, inv.sii_message, inv.sii_receipt)
            if inv.sii_result == 'Aceptado':
                inv.send_envelope_recipient(
                    RUTEmisor, resol_data, documentos, signature_d, SubTotDTE,
                    is_doc_type_b, file_name, company_id, certp)
                inv.get_pdf_docsonline()

    @api.multi
    def ask_for_dte_status(self):
        """
        Este proceso realiza las consultas desde la cola de envío.
        :return:
        """
        if self.company_id.dte_service_provider not in ['LIBREDTE']:
            if self.sii_message and self.sii_receipt:
                _logger.info('ask_for_dte_status %%%%%%%%%% ya hay estado....')
                self.sii_result = self.analyze_sii_result(
                    self.sii_result, self.sii_message, self.sii_receipt)
                # aca hacer los procesos nuevos
                SubTotDTE = '''<SubTotDTE>
   <TpoDTE>{}</TpoDTE>
   <NroDTE>1</NroDTE>
</SubTotDTE>'''.format(self.sii_document_class_id.sii_code)
                signature_d = self.get_digital_signature_pem(self.company_id)
                certp = signature_d['cert'].replace(BC, '').replace(
                    EC, '').replace('\n', '')
                if self.sii_result == 'Aceptado':
                    self.send_envelope_recipient(
                        self.format_vat(self.company_id.vat),
                        self.get_resolution_data(self.company_id),
                        self.sii_xml_request, signature_d, SubTotDTE, False,
                        self.sii_send_file_name, self.company_id, certp)
                    # prepara para poder enviar los archivos.
                return

            if True:  # try:
                signature_d = self.get_digital_signature_pem(
                    self.company_id)
                seed = self.get_seed(self.company_id)
                template_string = self.create_template_seed(seed)
                seed_firmado = self.sign_seed(
                    template_string, signature_d['priv_key'],
                    signature_d['cert'])
                token = self.get_token(seed_firmado, self.company_id)
                _logger.info('ask_for_dte_status token: {}'.format(token))
            else:  # except:
                _logger.info(connection_status)
                raise UserError(connection_status)
            if not self.sii_send_ident:
                raise UserError(
                    'No se ha enviado aún el documento, aún está en cola de \
envío interna en odoo')
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
    mnt_exe = fields.Float('Monto exento de la factura')
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
        ('EnCola', 'En cola de envío'),
        ('Enviado', 'Enviado'),
        ('Proceso', 'Proceso'),
        ('Reparo', 'Reparo'),
        ('Aceptado', 'Aceptado'),
        ('Rechazado', 'Rechazado'),
        ('Reenviar', 'Reenviar'),
        ('Anulado', 'Anulado')],
        'Resultado',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        help="SII request result",
        default='')
    canceled = fields.Boolean(string="Canceled?")
    estado_recep_dte = fields.Selection(
        [('no_revisado', 'No Revisado'),
            ('0', 'Conforme'),
            ('1', 'Error de Schema'),
            ('2', 'Error de Firma'),
            ('3', 'RUT Receptor No Corresponde'),
            ('90', 'Archivo Repetido'),
            ('91', 'Archivo Ilegible'),
            ('99', 'Envio Rechazado - Otros')],
        string="Estado de Recepcion del Envio")
    estado_recep_glosa = fields.Char(
        string="Información Adicional del Estado de Recepción")
    sii_send_file_name = fields.Char(string="Send File Name")
    responsable_envio = fields.Many2one('res.users', string='Responsable Envío')
    ticket = fields.Boolean(
        string="Formato Ticket", default=False, readonly=True,
        states={'draft': [('readonly', False)]})
    dte_service_provider = fields.Selection(
        [('', 'None'),
         ('FACTURACION', 'facturacion.cl'),
         ('LIBREDTE', 'LibreDTE'),
         ('SIIHOMO', 'SII - Certification process'),
         ('SII', 'www.sii.cl'),
         ('SII MiPyme', 'SII - Portal MiPyme'),
         ], 'DTE Service Provider',
        related='company_id.dte_service_provider',
        readonly=True)
    docs_online_token = fields.Char('Documentos Online')

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
        # if call_model == 'stock.picking' or \
        #                 self._context['active_model'] == 'stock.picking':
        #     inv = self.env['stock.picking'].browse(
        #         self._context['active_id'])
        #     sii_code = 52
        # else:
        if True:
            self.ensure_one()
            inv = self
            sii_code = inv.sii_document_class_id.sii_code
            folio = self.get_folio_current()
        try:
            if not folio:
                folio = foliop
        except:
            folio = foliop
        emisor = self.format_vat(inv.company_id.vat)
        _logger.info('entrada a bring_generated_xml_ldte. Folio: {}'.format(
            folio))
        if headers == '':
            headers = self.create_headers_ldte()
        _logger.info('headers: {}'.format(headers))
        _logger.info(api_get_xml.format(sii_code, folio, emisor))
        response_xml = pool.urlopen(
            'GET', api_get_xml.format(sii_code, folio, emisor),
            headers=headers)
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

    def bring_xml_ldte(self, response_emitir_data, headers=''):
        """
        Función para tomar el XML generado en libreDTE y adjuntarlo al registro
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-23
        """
        _logger.info('entrada a bringxml function')
        if headers == '':
            headers = self.create_headers_ldte()
        _logger.info('api: {}, headers: {}, body: {}'.format(
            api_generar, headers, response_emitir_data))
        response_generar = pool.urlopen(
            'POST', api_generar, headers=headers,
            body=response_emitir_data)
        if response_generar.status != 200:
            raise UserError('Error en conexión al generar: {}, {}'.format(
                response_generar.status, response_generar.data))
        _logger.info('response_generar: {}'.format(response_generar.data))
        self.sii_xml_response = response_emitir_data
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
            _logger.info(self.sii_document_class_id.name)
            _logger.info(response_j['folio'])
            attachment_id = attachment_obj.create(
                {
                    'name': 'DTE_'+self.sii_document_class_id.name+'-'+str(
                        response_j['folio'])+'.xml',
                    'datas': response_j['xml'],
                    'datas_fname': 'DTE_'+self.sii_document_class_id.name+'-'+str(
                        response_j['folio'])+'.xml',
                    'res_model': self._name,
                    'res_id': self.id,
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
                'POST', api_gen_pdf, headers=headers,
                body=generar_pdf_request)
            if response_pdf.status != 200:
                raise UserError('Error en conexión al generar: {}, {}'.format(
                    response_pdf.status, response_pdf.data))
            invoice_pdf = base64.b64encode(response_pdf.data)
            attachment_name = self.get_attachment_name(
                inv, call_model=str(inv._name))
            attachment_obj = self.env['ir.attachment']
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
        for inv in self.with_context(lang='es_CL'):
            if inv.type[:2] == 'in':
                continue
            if inv.sii_send_ident:
                _logger.info(
                    'Track id existente. No se enviará documento: {}'.format(
                        inv.sii_send_ident))
                if not inv.sii_xml_request:
                    inv.sii_result = 'NoEnviado'
                continue
            inv.sii_result = 'NoEnviado'
            inv.responsable_envio = self.env.user.id
            if inv.type in ['out_invoice', 'out_refund'] and \
                    inv.company_id.dte_service_provider in ['SII', 'SIIHOMO']:
                inv._do_stamp()
            elif inv.type in ['out_invoice', 'out_refund'] and \
                    inv.company_id.dte_service_provider not in [
                        'SII', 'SIIHOMO']:
                tpo_dte = inv._tpo_dte()
                # dte = collections.OrderedDict()
                # dte[tpo_dte + ' ID'] = inv._dte()
                dte = inv._dte()
                _logger.info(
                    'DTE desde action inv open {}'.format(json.dumps(dte)))
                headers = self.create_headers_ldte()
                response_j = self.enviar_ldte(dte, headers)
                inv.write(
                    {
                        'sii_result': 'Enviado',
                        'sii_send_ident': response_j['track_id']})
                _logger.info('se guardó xml con la factura')
                inv.set_folio(inv, response_j['folio'])

        super(Invoice, self).action_invoice_open()

    @api.multi
    def do_dte_send_invoice(self, att_number=None, dte=False):
        ids = []
        for inv in self.with_context(lang='es_CL'):
            if inv.sii_result in ['', 'NoEnviado', 'Rechazado']:
                if inv.sii_result in ['Rechazado']:
                    inv._do_stamp()
                inv.sii_result = 'EnCola'
                ids.append(inv.id)
        if not isinstance(att_number, unicode):
            att_number = ''
        if ids and self.check_if_not_sent(ids, 'account.invoice', 'envio'):
            # ordenas los ids.sort()
            # preparar el envio sii
            self.env['sii.cola_envio'].create({
                'doc_ids': ids,
                'model': 'account.invoice',
                'user_id': self.env.user.id,
                'tipo_trabajo': 'envio',
                'att_number': att_number, })

    @api.multi
    def get_barcode(self, no_product=False):
        ted = False
        folio = self.get_folio()
        result['TED']['DD']['RE'] = self.format_vat(self.company_id.vat)
        result['TED']['DD']['TD'] = self.sii_document_class_id.sii_code
        result['TED']['DD']['F'] = folio
        result['TED']['DD']['FE'] = self.date_invoice
        if not self.partner_id.vat:
            raise UserError(_("Fill Partner VAT"))
        result['TED']['DD']['RR'] = self.format_vat(self.partner_id.vat)
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
        # antes de firmar, formatear
        root = etree.XML(ddxml)
        # formateo sin remover indents
        ddxml = etree.tostring(root)
        timestamp = self.time_stamp()
        ddxml = ddxml.replace('2014-04-24T12:02:20', timestamp)
        frmt = self.signmessage(ddxml, keypriv, keypub)['firma']
        ted = (
            '''<TED version="1.0">{}<FRMT algoritmo="SHA1withRSA">{}\
</FRMT></TED>''').format(ddxml, frmt)
        root = etree.XML(ted)
        self.sii_barcode = ted
        if ted:
            barcodefile = StringIO()
            image = self.pdf417bc(ted)
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
