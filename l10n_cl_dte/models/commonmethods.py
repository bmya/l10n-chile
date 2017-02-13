# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging, json
from lxml import etree
from lxml.etree import Element, SubElement
import collections
import urllib3
import xmltodict
from elaphe import barcode
import M2Crypto
import base64
import hashlib
from SOAPpy import SOAPProxy
from signxml import xmldsig, methods
import textwrap
try:
    urllib3.disable_warnings()
except:
    pass
_logger = logging.getLogger(__name__)
"""
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import OpenSSL
from OpenSSL.crypto import *"""
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

"""
Diccionario para normalizar datos y emplear en diversos tipos de documentos
a Futuro.
La idea es cambiar la manera en que se rellenan, normalizan, y validan los
tags, mediante una forma unificada y tendiendo a usar decoradores y funciones
para todas las finalidades.
Además esta parte de la implementación, para mejor efectividad se deberá migrar
a una biblioteca separada, de manera que se pueda acceder desde diferentes
addons: permitiendo así seguir el principio "DRY" de Python.
el value[0] de la lista representa la longitud admitida
Propuesta:
todo: el value[1] si es obligatorio o no
todo: el value[2] puede ser la llamada a funcion para validar
todo: el value[3] el nombre de campo mapeado en Odoo
@author: Daniel Blanco Martín daniel[at]blancomartin.cl
@version: 2017-02-11
"""


class CommonMethods:

    @staticmethod
    def format_vat(value):
        ''' Se Elimina el 0 para prevenir problemas con el sii, ya que las
        muestras no las toma si va con
        el 0 , y tambien internamente se generan problemas'''
        if not value or value == '' or value == 0:
            value ="CL666666666"
            #@TODO opción de crear código de cliente en vez de rut genérico
        rut = value[:10] + '-' + value[10:]
        rut = rut.replace('CL0', '').replace('CL', '')
        return rut

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


class LibreDte():

    host = 'https://libredte.cl/api'
    api_emitir = host + '/dte/documentos/emitir'
    api_generar = host + '/dte/documentos/generar'
    api_gen_pdf = host + '/dte/documentos/generar_pdf'
    api_get_xml = host + '/dte/dte_emitidos/xml/{0}/{1}/{2}'
    api_upd_status = host + '/dte/dte_emitidos/actualizar_estado/'
    no_product = False

    @staticmethod
    def remove_plurals_node(dte):
        dte1 = OrderedDict()
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

    def enviar_ldte(self, inv, dte, headers):
        """
        Función para enviar el dte a libreDTE
        @author: Daniel Blanco
        @version: 2017-02-11
        :param headers:
        :param dte:
        :return:
        """
        dte['Encabezado']['Emisor'] = self.remove_plurals_node(
            dte['Encabezado']['Emisor'])
        dte = cm.remove_plurals_node(dte)
        dte = cm.char_replace(dte)
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
            inv.sii_xml_response = response_emitir.data
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
        response_j = self.bring_xml_ldte(
            inv, response_emitir_data, headers=headers)
        _logger.info('vino de bring_xml_dte')
        _logger.info('response_j')
        _logger.info(response_j)
        return response_j


class PySIIDTE():

    @staticmethod
    def create_template_doc(doc):
        """
        Creacion de plantilla xml para envolver el DTE
        Previo a realizar su firma (1)
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-01
        """
        xml = '''<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
    <!-- Odoo Implementation Blanco Martin -->
    {}</DTE>'''.format(doc)
        return xml

    @staticmethod
    def split_cert(cert):
        certf, j = '', 0
        for i in range(0, 29):
            certf += cert[76 * i:76 * (i + 1)] + '\n'
        return certf

    @staticmethod
    def create_template_envio(RutEmisor, RutReceptor, FchResol, NroResol,
                              TmstFirmaEnv, EnvioDTE,signature_d,SubTotDTE):
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
        xml = '''<SetDTE ID="SetDoc">
<Caratula version="1.0">
<RutEmisor>{0}</RutEmisor>
<RutEnvia>{1}</RutEnvia>
<RutReceptor>{2}</RutReceptor>
<FchResol>{3}</FchResol>
<NroResol>{4}</NroResol>
<TmstFirmaEnv>{5}</TmstFirmaEnv>
{6}</Caratula>{7}
</SetDTE>
'''.format(RutEmisor, signature_d['subject_serial_number'], RutReceptor,
           FchResol, NroResol, TmstFirmaEnv, SubTotDTE, EnvioDTE)
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
        url = server_url[company_id.dte_service_provider] + 'CrSeed.jws?WSDL'
        ns = 'urn:' + server_url[company_id.dte_service_provider] + 'CrSeed.jws'
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
        doc = etree.fromstring(message)
        signed_node = xmldsig(
            doc, digest_algorithm=u'sha1').sign(
            method=methods.enveloped, algorithm=u'rsa-sha1',
            key=privkey.encode('ascii'),
            cert=cert)
        msg = etree.tostring(
            signed_node, pretty_print=True).replace('ds:', '')
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
        url = server_url[company_id.dte_service_provider] + 'GetTokenFromSeed.jws?WSDL'
        ns = 'urn:' + server_url[company_id.dte_service_provider] +'GetTokenFromSeed.jws'
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
            'sig': 'xmldsignature_v10.xsd'}
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
            raise UserError(_('XML Malformed Error: {}').format(e.args))

    def send_xml_file(
            self, envio_dte=None, file_name="envio", company_id=False,
            sii_result='NoEnviado', doc_ids=''):
        if not company_id.dte_service_provider:
            raise UserError(_("Not Service provider selected!"))
        #try:
        signature_d = self.get_digital_signature_pem(
            company_id)
        seed = self.get_seed(company_id)
        template_string = self.create_template_seed(seed)
        seed_firmado = self.sign_seed(
            template_string, signature_d['priv_key'],
            signature_d['cert'])
        token = self.get_token(seed_firmado, company_id)
        #except:
        #    _logger.info('error')
        #    return

        url = 'https://palena.sii.cl'
        if company_id.dte_service_provider == 'SIIHOMO':
            url = 'https://maullin.sii.cl'
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
            'Cookie': 'TOKEN={}'.format(token),
        }
        params = collections.OrderedDict()
        params['rutSender'] = signature_d['subject_serial_number'][:8]
        params['dvSender'] = signature_d['subject_serial_number'][-1]
        params['rutCompany'] = company_id.vat[2:-1]
        params['dvCompany'] = company_id.vat[-1]
        params['archivo'] = (file_name,envio_dte, "text/xml")
        multi  = urllib3.filepost.encode_multipart_formdata(params)
        headers.update({'Content-Length': '{}'.format(len(multi[0]))})
        response = pool.request_encode_body('POST', url+post, params, headers)
        retorno = {
            'sii_xml_response': response.data,
            'sii_result': 'NoEnviado',
            'sii_send_ident': ''}
        if response.status != 200:
            return retorno
        respuesta_dict = xmltodict.parse(response.data)
        if respuesta_dict['RECEPCIONDTE']['STATUS'] != '0':
            _logger.info(
                connection_status[respuesta_dict['RECEPCIONDTE']['STATUS']])
        else:
            retorno.update(
                {'sii_result': 'Enviado',
                 'sii_send_ident': respuesta_dict['RECEPCIONDTE']['TRACKID']})
        return retorno

    def sign_full_xml(self, message, privkey, cert, uri, type='doc'):
        doc = etree.fromstring(message)
        string = etree.tostring(doc[1])
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
