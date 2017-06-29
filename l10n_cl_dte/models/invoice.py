# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import base64
import collections
import hashlib
import json
import logging
import os
import textwrap
from datetime import datetime, timedelta

import cchardet
import dicttoxml
import M2Crypto
import pysiidte
import pytz
import requests
import urllib3
import xmltodict
from elaphe import barcode
from lxml import etree
from lxml.etree import Element, SubElement
from signxml import XMLSigner, methods
from SOAPpy import SOAPProxy

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    urllib3.disable_warnings()
except:
    pass
_logger = logging.getLogger(__name__)
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

normalize_tags = pysiidte.normalize_tags
pluralizeds = pysiidte.pluralizeds
result = xmltodict.parse(pysiidte.stamp)
server_url = pysiidte.server_url
BC = pysiidte.BC
EC = pysiidte.EC

try:
    pool = urllib3.PoolManager()
except:
    pass
connection_status = pysiidte.connection_status
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace(
    '/models', '/static/xsd/')
no_product = False


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


def db_query(method):
    def call(self, *args, **kwargs):
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


class Signer(XMLSigner):
    def __init__(self):
        super(Signer, self).__init__(
            method=methods.detached,
            signature_algorithm='rsa-sha1',
            digest_algorithm='sha1',
            c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')

    @staticmethod
    def key_value_serialization_is_required(cert_chain):
        return True


class Invoice(models.Model):
    """
    Extension of data model to contain global parameters needed
    for all electronic invoice integration.
    @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    @version: 2016-06-11
    """
    _inherit = "account.invoice"

    @db_query
    def get_net_ex_detail(self):
        return """
        /*
        DETALLE DE MONTOS
        */
        select
        invoice_id,
        line_id,
        price_subtotal,
        /* al_pname, */
        /* at_name, */
        tax_amount,
        (CASE
        WHEN tax_amount != 0 THEN 0
        ELSE (CASE
            WHEN price_subtotal > 0 THEN price_subtotal
            ELSE 0
        END)
        END) as mntexe,
        (CASE
        WHEN tax_amount > 0 THEN price_subtotal
        ELSE 0
        END) as mntneto,
        (CASE
        WHEN price_subtotal < 0 and tax_amount < 0 then abs(price_subtotal)
        ELSE 0
        END) as dcglobalaf,
        (CASE
        WHEN price_subtotal < 0 and tax_amount is null THEN abs(price_subtotal)
        ELSE 0
        END) as dcglobalex
        from
        (select
        al.invoice_id as invoice_id,
        al.id as line_id,
        al.price_subtotal,
        al.product_id,
        al.name as al_pname,
        at.name as at_name,
        at.tax_group_id,
        at.amount,
        round(al.price_subtotal * at.amount / 100) as tax_amount,
        at.no_rec,
        at.retencion,
        at.sii_code,
        at.type_tax_use
        from account_invoice_line al
        left join account_invoice_line_tax alt
        on al.id = alt.invoice_line_id
        left join account_tax at
        on alt.tax_id = at.id
        where al.company_id = 1
        and al.invoice_id = %s) as a
        order by line_id
        """ % self.id

    @db_query
    def get_net_ex_amount(self):
        return """
        /*
        SUMA DE MONTOS
        */
        select
        invoice_id,
        sum(price_subtotal) as sum_subtotal,
        sum(tax_amount) as sum_taxes,
        sum((CASE
        WHEN tax_amount != 0 THEN 0
        ELSE (CASE
            WHEN price_subtotal > 0 THEN price_subtotal
            ELSE 0
        END)
        END)) as mntexe,
        sum((CASE
        WHEN tax_amount > 0 THEN price_subtotal
        ELSE 0
        END)) as mntneto,
        0 as mntnf,
        sum((CASE
        WHEN price_subtotal < 0 and tax_amount < 0 then abs(price_subtotal)
        ELSE 0
        END)) as dcglobalaf,
        sum((CASE
        WHEN price_subtotal < 0 and tax_amount is null THEN abs(price_subtotal)
        ELSE 0
        END)) as dcglobalex,
        0 as dcglobalnf
        from
        (select
        al.invoice_id as invoice_id,
        al.id as line_id,
        al.price_subtotal,
        al.product_id,
        al.name as al_pname,
        at.name as at_name,
        at.tax_group_id,
        at.amount,
        round(al.price_subtotal * at.amount / 100) as tax_amount,
        at.no_rec,
        at.retencion,
        at.sii_code,
        at.type_tax_use
        from account_invoice_line al
        left join account_invoice_line_tax alt
        on al.id = alt.invoice_line_id
        left join account_tax at
        on alt.tax_id = at.id
        where al.company_id = 1
        and al.invoice_id = %s) as a
        group by invoice_id
        """ % self.id

    # metodos comunes
    @staticmethod
    def safe_variable(var, key):
        len = normalize_tags[key][0]
        try:
            msg = normalize_tags[key][1][:len]
        except:
            msg = u'variable'
        try:
            var = var[:len]
        except:
            raise UserError(
                u'{} - {} no está configurada.'.format(key, msg))
        return var

    def default_variable(self, var, key):
        defaults = {
            'GiroEmis': 'invoice_turn'
        }
        len = normalize_tags[key][0]
        try:
            msg = normalize_tags[key][1]
        except:
            msg = u'variable'
        try:
            var = var[:len]
        except:
            var = getattr(self, defaults[key][0])
        return var

    def format_vat(self, value):
        _logger.info('rut.....%%%%%%%%%%%%%'.format(value))
        if not value or value == '' or value == 0:
            value = self.partner_id.document_number.replace('.', '')
            if not value:
                raise UserError(
                    u'RUT no encontrado para este cliente o RUT \
                    inválido {} - {} - {}'.format(
                        self.partner_id.name, self.partner_id.vat,
                        self.partner_id.document_number))
        else:
            value = (value[:10] + '-' + value[10:]).replace(
                'CL0', '').replace('CL', '')
        return value

    @staticmethod
    def _calc_discount_vat(discount, sii_code=0):
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
        var = pysiidte.char_replace(var)
        _logger.info('var: {}, key: {}, control: {}')
        if isinstance(key, (int, long, float, complex)):
            size = key
            control = 'truncate'
        else:
            size = normalize_tags[key][0]
        if control == 'truncate':
            var = var[:size]
        elif control == 'safe':
            var = self.safe_variable(var, key)
        return var

    @api.model
    def check_if_not_sent(self, ids, model, job):
        queue_obj = self.env['sii.cola_envio']
        item_ids = queue_obj.search(
            [('doc_ids', 'like', ids), ('model', '=', model),
             ('tipo_trabajo', '=', job)])
        return len(item_ids) <= 0

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
        print "&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&"
        _logger.error(xml)
        return xml

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
                _(u'Error de formación del XML: {} - Validación: {}').format(
                    e.args, validacion))

    def send_xml_file(self, envio_dte=None, file_name="envio", company_id=False,
                      sii_result='NoEnviado', doc_ids=''):
        if not company_id.dte_service_provider:
            raise UserError(_("Not Service provider selected!"))
        signature_d = self.get_digital_signature_pem(company_id)
        # template_string = pysiidte.get_seed(
        #     self.company_id.dte_service_provider)
        # # template_string = self.create_template_seed(seed)
        # seed_firmado = self.sign_seed(
        #     template_string, signature_d['priv_key'],
        #     signature_d['cert'])
        # token = pysiidte.get_token(
        #     seed_firmado, company_id.dte_service_provider)
        token = pysiidte.sii_token(
            company_id.dte_service_provider, signature_d['priv_key'],
            signature_d['cert'])
        url = server_url[company_id.dte_service_provider].replace(
            '/DTEWS/', '')
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
        response = pool.request_encode_body(
            'POST', url + post, params, headers)
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
        signature_value.text = textwrap.fill(
            base64.b64encode(signature), 64)
        key_info = SubElement(sig_root, "KeyInfo")
        key_value = SubElement(key_info, "KeyValue")
        rsa_key_value = SubElement(key_value, "RSAKeyValue")
        modulus = SubElement(rsa_key_value, "Modulus")
        key = load_pem_private_key(
            privkey.encode('ascii'), password=None,
            backend=default_backend())
        modulus.text = textwrap.fill(
            base64.b64encode(
                self.long_to_bytes(
                    key.public_key().public_numbers().n)), 64)
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
            _logger.info('Encoding:')
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
        xml = dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).replace('<item>', '') \
            .replace('</item>', '').replace('<TEDd>', '') \
            .replace('</TEDd>', '').replace(
            '</{}_ID>'.format(tpo_dte),
            '\n{}\n</{}_ID>'.format(ted, tpo_dte))
        return xml

    def get_digital_signature_pem(self, comp_id):
        obj = user = False
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

    def get_pdf_file(self):
        """
        Funcion para descargar el attachment en el sistema local del usuario
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-05-01
        """
        attachment_obj = self.env['ir.attachment']
        attachment_id = attachment_obj.search(
            [('name', 'ilike', 'pdf'),
             ('res_model', '=', self._name),
             ('res_id', '=', self.id)])
        # raise UserError(attachment_id[0].id)
        _logger.info('DOWNLOOOOOOOAAAAAAAADDDDDDDD')
        url = '/web/content/%s?download=true' % attachment_id[0].id
        _logger.info(url)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self', }

    def get_xml_file(self):
        """
        Funcion para descargar el attachmnet en el sistema local del usuario
         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
         @version: 2016-05-01
        """
        filename = (self.document_number+'.xml').replace(' ','')
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=account.invoice\
&field=sii_xml_request&id=%s&filename=%s' % (self.id,filename),
            'target': 'self', }

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
        en el rango del CAF.
        Nota Daniel Blanco: Se agrega una opción para evitar el timbrado de un
        folio anterior al caf actual.
        """
        caffiles = self.journal_document_class_id.sequence_id.dte_caf_ids
        folio = self.get_folio()
        if not caffiles:
            raise UserError(_('''There is no CAF file available or in use \
for this Document. Please enable one.'''))
        else:
            for caffile in caffiles:
                post = base64.b64decode(caffile.caf_file)
                post = xmltodict.parse(post.replace(
                    '<?xml version="1.0"?>', '', 1))
                doc_type = post['AUTORIZACION']['CAF']['DA']['TD']
                folio_inicial = post['AUTORIZACION']['CAF']['DA']['RNG']['D']
                folio_final = post['AUTORIZACION']['CAF']['DA']['RNG']['H']
                if int(self.sii_document_class_id.sii_code) != int(doc_type):
                    raise UserError('''El tipo de documento del caf {} no es \
igual al tipo de documento realizado {}'''.format(
                        doc_type, self.sii_document_class_id.sii_code))
                if folio in range(int(folio_inicial), (int(folio_final)+1)):
                    return post
            if folio > int(folio_final):
                msg = '''El folio de este documento: {} está fuera de rango \
del CAF vigente (desde {} hasta {}). Solicite un nuevo CAF en el sitio \
www.sii.cl'''.format(folio, folio_inicial, folio_final)
                # defino el status como "spent"
                caffile.status = 'spent'
                raise UserError(_(msg))
            elif folio < int(folio_inicial):
                msg = '''El folio de este documento: {} es anterior al rango
del CAF encontrado (desde {} hasta {}).'''.format(
                    folio, folio_inicial, folio_final)
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
        if not self.turn_issuer.name:
            self.turn_issuer = self.company_id.company_activities_ids[0]
        emisor = collections.OrderedDict()
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
            # if not self.invoice_turn.name:
            #     raise UserError('El giro del cliente no está definido')
            receptor['GiroRecep'] = self.normalize_string(
                self.invoice_turn.name, 'GiroRecep', 'truncate')
        if self.partner_id.phone:
            receptor['Contacto'] = self.normalize_string(
                self.partner_id.phone, 'Contacto', 'truncate')
        if self.partner_id.dte_email and not self.is_doc_type_b():
            receptor['CorreoRecep'] = self.partner_id.dte_email
        receptor['DirRecep'] = self.normalize_string(
            '%s %s' % (
                self.partner_id.street or '',
                self.partner_id.street2 or ''), 'DirRecep', 'safe')
        receptor['CmnaRecep'] = self.normalize_string(
            self.partner_id.city_id.name, 'CmnaRecep', 'safe')
        receptor['CiudadRecep'] = self.normalize_string(
            self.partner_id.city, 'CiudadRecep', 'safe')
        return receptor

    def _discounts(self, global_amounts):
        _logger.info(json.dumps(global_amounts))
        discount_types = [
            ('dcglobalaf', 'mntneto'),
            ('dcglobalex', 'mntexe'),
            ('dcglobalnf', 'mntnf'), ]
        discounts = []
        for i in range(0, 3):
            j = 1
            try:
                if global_amounts[discount_types[i][0]] == 0:
                    continue
            except:
                continue
            discount = {'DscRcgGlobal': collections.OrderedDict()}
            # _logger.info(json.dumps(discounts))
            # discounts[i]['DscRcgGlobal'] = collections.OrderedDict()
            discount['DscRcgGlobal']['NroLinDR'] = j
            discount['DscRcgGlobal']['TpoMov'] = 'D'
            # discounts[i]['DscRcgGlobal']['GlosaDR'] =
            discount['DscRcgGlobal']['TpoValor'] = '%'
            try:
                discount['DscRcgGlobal']['ValorDR'] = round(
                    100 * abs(global_amounts[discount_types[i][0]])/float(
                        global_amounts[discount_types[i][1]]), 2)
            except ZeroDivisionError:
                raise UserError(u"""Está aplicando un tipo de descuento exento \
sobre un valor afecto o a la inversa. Revise los descuentos que intenta \
realizar en su documento.""")
            discount['DscRcgGlobal']['IndExeDR'] = i
            j += 1
            discounts.append(discount)
        # raise UserError(json.dumps(discounts))
        return discounts

    def _totals(self, MntExe=0, no_product=False, tax_include=False,
                global_discount=0):
        totals = collections.OrderedDict()
        # esto sobreescribe el calculo del mntexe que viene por parametros
        # para hacer: corregir desde antes, o cambiar el metodo de calcular
        # para hacer: el mntexe siempre existe solo que si no hay neto, se
        # debe validar que el tipo de documento valido para estos casos debe
        # ser exenta
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
                self.mnt_exe = totals['MntExe'] = int(round(MntExe, 0))
            if not self.is_doc_type_b() or not tax_include:
                if IVA:
                    if not self.is_doc_type_b():
                        totals['TasaIVA'] = round(IVA.tax_id.amount, 2)
                    totals['IVA'] = int(round(IVA.amount, 0))
                if no_product:
                    totals['MntNeto'] = 0
                    if not self.is_doc_type_b():
                        totals['TasaIVA'] = 0
                    totals['IVA'] = 0
            if IVA and IVA.tax_id.sii_code in [15]:
                totals['ImptoReten'] = collections.OrderedDict()
                totals['ImptoReten']['TpoImp'] = IVA.tax_id.sii_code
                totals['ImptoReten']['TasaImp'] = round(IVA.tax_id.amount, 2)
                totals['ImptoReten']['MontoImp'] = int(round(IVA.amount))
        _logger.info('_totals: {}'.format(global_discount))
        # raise UserError('_totals:')
        monto_total = int(round(self.amount_total, 0))
        if no_product:
            monto_total = 0
        totals['MntTotal'] = monto_total
        try:
            if totals['MntExe'] > 0 and totals['MntTotal'] <= totals['MntExe'] \
                    and self.sii_document_class_id.sii_code not in [
                        34, 38, 41, 56, 61, 110, 112, ]:
                raise UserError(u"""Ud. ha seleccionado un tipo de documento \
incorrecto para facturación exenta. Seleccione el documento adecuado.""")
        except KeyError:
            pass
#             raise UserError(u"""Ud. esta aplicando un descuento exento sobre \
# items afectos. Agregue el IVA al descuento o use un item Descuento que tenga \
# iva.""")
        return totals

    def _encabezado(self, MntExe=0, no_product=False, tax_include=False,
                    global_discount=0):
        encabezado = collections.OrderedDict()
        encabezado['IdDoc'] = self._id_doc(tax_include, MntExe)
        encabezado['Emisor'] = self._sender()
        encabezado['Receptor'] = self._receptor()
        encabezado['Totales'] = self._totals(
            MntExe=MntExe, no_product=no_product,
            global_discount=global_discount)
        return encabezado

    def _invoice_lines(self, global_discount=0):
        line_number = 1
        invoice_lines = []
        no_product = False
        MntExe = 0
        prexe = self.get_net_ex_detail()
        for line in self.invoice_line_ids:
            try:
                if line.product_id.is_discount:
                    global_discount += int(round(line.price_subtotal, 0))
                    global_discount = self._calc_discount_vat(
                        global_discount)
                    # sum_lines += line.price_subtotal
                    continue
            except:
                if u'descuento' in line.product_id.name.lower() \
                        or u'discount' in line.product_id.name.lower():
                    if line.quantity > 0:
                        raise UserError(u'Para aplicar un descuento la \
cantidad debe ser negativa.')
                    global_discount = True
                    continue
                else:
                    global_discount = False
            if line.product_id.default_code == 'NO_PRODUCT':
                no_product = True
            lines = collections.OrderedDict()
            lines['NroLinDet'] = line_number
            if line.product_id.default_code and not no_product:
                lines['CdgItem'] = collections.OrderedDict()
                lines['CdgItem']['TpoCodigo'] = 'INT1'
                lines['CdgItem']['VlrCodigo'] = line.product_id.default_code
            tax_include = False
            for pr in prexe:
                if pr['line_id'] == line.id:
                    if pr['mntexe'] != 0:
                        lines['IndExe'] = 1
                        break
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
            if line.price_unit < 0:
                raise UserError(u"""El valor unitario no puede ser menor que 0.
Si necesita representar un descuento global, deberá utilizar el item \
'descuento', en cuyo caso las unidades deben ser negativas.""")
            if not no_product:
                lines['QtyItem'] = qty
            if qty == 0 and not no_product:
                lines['QtyItem'] = 1
            if not no_product:
                lines['UnmdItem'] = line.uom_id.name[:4]
                lines['PrcItem'] = int(round(line.price_unit, 2))
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
            'tax_include': tax_include,
            'global_discount': global_discount, }

    def _dte(self, att_number=None):
        dte = collections.OrderedDict()
        invoice_lines = self._invoice_lines()
        # ver de discontinuar _invoice_lines y replazar por get_net_ex_amount
        global_amounts = self.get_net_ex_amount()[0]
        MntExe = global_amounts['mntexe'] - global_amounts['dcglobalex']
        MntNeto = global_amounts['mntneto']
        global_discount = global_amounts['dcglobalaf'] + \
                          global_amounts['dcglobalex']
        dte['Encabezado'] = self._encabezado(
            MntExe, invoice_lines['no_product'], invoice_lines['tax_include'],
            global_discount)
        # try:
        #     MntNeto = dte['Encabezado']['Totales']['MntNeto']
        # except:
        #     MntNeto = 0
        _logger.info('_dte: global_discount: {}'.format(global_discount))
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
        if global_amounts['dcglobalaf'] > 0 or \
                        global_amounts['dcglobalex'] > 0 or \
                        global_amounts['dcglobalnf'] > 0:
            dte['DscRcgGlobals'] = self._discounts(global_amounts)
        if len(ref_lines) > 0:
            dte['Referencias'] = ref_lines
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
        xml_pret = pysiidte.remove_plurals_xml(xml_pret).replace(
            '<IndExeDR>0</IndExeDR>', '')
        envelope_efact = self.convert_encoding(xml_pret, 'ISO-8859-1')
        envelope_efact = pysiidte.create_template_doc(envelope_efact)
        _logger.info('envelope_efact: {}'.format(envelope_efact))
        type = 'bol' if self.is_doc_type_b() else 'doc'
        #    type = 'bol'
        einvoice = self.sign_full_xml(
            envelope_efact, signature_d['priv_key'],
            self.split_cert(certp), doc_id_number, type)
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
            if True:  # try:
                _logger.info('entrando en linea 1684')
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
            else:  # except:
                raise UserError('_get_dte_status: no se pudo obtener una \
respuesta satisfactoria por conexión ni de respuesta previa.')

    def save_xml_record(self, result, envio_dte, file_name):
        """
        Guarda el registro XML de las respuestas, pero no así el xml, el cual
        queda solamente con el DTE
        :param result:
        :param envio_dte:
        :param file_name:
        :return:
        """
        _logger.warning('save_xml_record %%%%%%%%%%%%%%%%%%%%%%%% {}'.format(
            self._context))
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
        _logger.error('send_envelope_sii (antes de crear envelope)')
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

    def _not_attachment(self, filetype):
        attachment_obj = self.env['ir.attachment']
        attachment_id = attachment_obj.search(
            [('name', 'ilike', filetype),
            ('res_model', '=', self._name),
            ('res_id', '=', self.id)])
        return not attachment_id

    def send_envelope_recipient(
            self, RUTEmisor, resol_data, documentos, signature_d, SubTotDTE,
            is_doc_type_b, file_name, company_id, certp):
        if self._not_attachment('pdf'):
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
        else:
            pass
        return self.get_pdf_file()

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

    def send_to_recipient(self):
        _logger.info('################3333333333333333333')
        _logger.info(self._context)
        raise UserError('kdkdkdkd')
        # hice esta funcion para invocar desde un botón ambos metodos
        self.send_envelope_recipient(
            RUTEmisor, resol_data, documentos, signature_d, SubTotDTE,
            is_doc_type_b, file_name, company_id, certp)
        self.get_pdf_docsonline()

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
                inv._do_stamp(att_number)
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
        dtes = {}  # otro diccionario mas y van 3
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
        envelope = False
        if not is_doc_type_b:
            envelope = self.send_envelope_sii(
                RUTEmisor, resol_data, documentos, signature_d, SubTotDTE,
                file_name, company_id, certp)
        for inv in self:
            inv.sii_result = pysiidte.analyze_sii_result(
                inv.sii_result, inv.sii_message, inv.sii_receipt)
            if inv.sii_result == 'Aceptado':
                # inv.send_to_recipient(
                #     RUTEmisor, resol_data, documentos, signature_d, SubTotDTE,
                #     is_doc_type_b, file_name, company_id, certp)
                inv.send_envelope_recipient(
                    RUTEmisor, resol_data, documentos, signature_d, SubTotDTE,
                    is_doc_type_b, file_name, company_id, certp)
                inv.get_pdf_docsonline()
        return envelope

    @api.multi
    def ask_force_dte(self):
        """
        Este proceso realiza las consultas desde la cola de envío.
        o desde el botón
        :return:
        """
        signature_d = self.get_digital_signature_pem(self.company_id)
        certp = signature_d['cert'].replace(BC, '').replace(
            EC, '').replace('\n', '')
        SubTotDTE = '''<SubTotDTE>
<TpoDTE>{}</TpoDTE>
<NroDTE>1</NroDTE>
</SubTotDTE>'''.format(self.sii_document_class_id.sii_code)
        return self.send_envelope_recipient(
            self.format_vat(self.company_id.vat),
            self.get_resolution_data(self.company_id),
            self.sii_xml_request, signature_d, SubTotDTE, False,
            self.sii_send_file_name, self.company_id, certp)
        # return

    @api.multi
    def ask_for_dte_status(self):
        """
        Este proceso realiza las consultas desde la cola de envío.
        o desde el botón
        :return:
        """
        signature_d = self.get_digital_signature_pem(self.company_id)
        certp = signature_d['cert'].replace(BC, '').replace(
            EC, '').replace('\n', '')
        if self.sii_message and self.sii_receipt:
            _logger.info('ask_for_dte_status - ya hay estado....')
            self.sii_result = pysiidte.analyze_sii_result(
                self.sii_result, self.sii_message, self.sii_receipt)
            # aca hacer los procesos nuevos
            SubTotDTE = '''<SubTotDTE>
<TpoDTE>{}</TpoDTE>
<NroDTE>1</NroDTE>
</SubTotDTE>'''.format(self.sii_document_class_id.sii_code)
            if self.sii_result == 'Aceptado':
                self.send_envelope_recipient(
                    self.format_vat(self.company_id.vat),
                    self.get_resolution_data(self.company_id),
                    self.sii_xml_request, signature_d, SubTotDTE, False,
                    self.sii_send_file_name, self.company_id, certp)
                return
        # seed = pysiidte.get_seed(self.company_id.dte_service_provider)
        # template_string = self.create_template_seed(seed)
        # seed_firmado = self.sign_seed(
        #     template_string, signature_d['priv_key'],
        #     signature_d['cert'])
        # token = pysiidte.get_token(
        #     seed_firmado, self.company_id.dte_service_provider)
        token = pysiidte.sii_token(
            self.company_id.dte_service_provider, signature_d['priv_key'],
            signature_d['cert'])
        if self.sii_result == 'Enviado':
            _logger.info('token: {}'.format(token))
            status = self._get_send_status(
                self.sii_send_ident, signature_d, token)
            if self.sii_result != 'Proceso':
                return status
        return self._get_dte_status(signature_d, token)

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
    def get_xml_attachment(self, inv=''):
        """
        Función para leer el xml desde los attachments
        @author: Daniel Blanco Martín (daniel[at]blancomartin.cl)
        @version: 2016-07-01
        """
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
    def action_invoice_open(self):
        if self.company_id.dte_service_provider in ['SII MiPyme']:
            super(Invoice, self).action_invoice_open()
            return
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
            if inv.type in ['out_invoice', 'out_refund']:
                inv._do_stamp()
        super(Invoice, self).action_invoice_open()
        self.do_dte_send_invoice()

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
            ids.sort()
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
        print result['TED']['DD']['RSR']
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
        # raise UserError('result caf: {}'.format(result['TED']['DD']['CAF']))
        _logger.info('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        print result
        print result['TED']
        print result['TED']['DD']
        print resultcaf['AUTORIZACION']
        result['TED']['DD']['CAF'] = resultcaf['AUTORIZACION']['CAF']
        timestamp = self.time_stamp()
        result['TED']['DD']['TSTED'] = timestamp
        dte = result['TED']['DD']
        # raise UserError(json.dumps(dte))
        dicttoxml.set_debug(False)
        ddxml = '<DD>'+dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).replace(
            '<key name="@version">1.0</key>', '', 1).replace(
            '><key name="@version">1.0</key>', ' version="1.0">', 1).replace(
            '><key name="@algoritmo">SHA1withRSA</key>',
            ' algoritmo="SHA1withRSA">').replace(
            '<key name="#text">', '').replace(
            '</key>', '').replace('<CAF>', '<CAF version="1.0">')+'</DD>'
        # prueva a remover para que no recodifique dos veces
        # ddxml = self.convert_encoding(ddxml, 'utf-8')
        keypriv = (resultcaf['AUTORIZACION']['RSASK']).encode(
            'latin-1').replace('\t', '')
        keypub = (resultcaf['AUTORIZACION']['RSAPUBK']).encode(
            'latin-1').replace('\t', '')
        # antes de firmar, formatear
        root = etree.XML(ddxml)
        # formateo sin remover indents
        ddxml = etree.tostring(root)
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
