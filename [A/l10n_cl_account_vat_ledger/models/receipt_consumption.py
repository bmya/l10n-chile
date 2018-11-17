# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
from lxml import etree
from lxml.etree import Element, SubElement
from lxml import objectify
from lxml.etree import XMLSyntaxError

import xml.dom.minidom
import pytz


import socket
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

#urllib3.disable_warnings()
pool = urllib3.PoolManager(timeout=30)

import textwrap

_logger = logging.getLogger(__name__)

try:
    import xmltodict
except ImportError:
    _logger.info('Cannot import xmltodict library')

try:
    import dicttoxml
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
    from signxml import xmldsig, methods
except ImportError:
    _logger.info('Cannot import signxml')

server_url = {'SIIHOMO':'https://maullin.sii.cl/DTEWS/','SII':'https://palena.sii.cl/DTEWS/'}

BC = '''-----BEGIN CERTIFICATE-----\n'''
EC = '''\n-----END CERTIFICATE-----\n'''

# hardcodeamos este valor por ahora
import os
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace('/models','/static/xsd/')

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

class ConsumoFolios(models.Model):
    _name = "account.move.receipt_consumption"

    sii_message = fields.Text(
        string='SII Message',
        copy=False,
        readony=True,
        states={'draft': [('readonly', False)]},)
    sii_xml_request = fields.Text(
        string='SII XML Request',
        copy=False,
        readony=True,
        states={'draft': [('readonly', False)]},)
    sii_xml_response = fields.Text(
        string='SII XML Response',
        copy=False,
        readony=True,
        states={'draft': [('readonly', False)]},)
    sii_send_ident = fields.Text(
        string='SII Send Identification',
        copy=False,
        readony=True,
        states={'draft': [('readonly', False)]},)
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
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user create invoice, an invoice number is generated. Its in open status till user does not pay invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    move_ids = fields.Many2many('account.move',
    	readony=True,
        states={'draft': [('readonly', False)]},)
    fecha_inicio = fields.Date(string="Fecha Inicio",
    	readony=True,
        states={'draft': [('readonly', False)]},)
    fecha_final = fields.Date(string="Fecha Final",
    	readony=True,
        states={'draft': [('readonly', False)]},)
    correlativo = fields.Integer(string="Correlativo",
    	readony=True,
        states={'draft': [('readonly', False)]},)
    sec_envio = fields.Integer(string="Secuencia de Envío",
    	readony=True,
        states={'draft': [('readonly', False)]},)
    #total_afecto = fields.Char(string="Total Afecto")
    #total_exento = fields.Char(string="Total Exento")
    company_id = fields.Many2one('res.company',
        required=True,
        default=lambda self: self.env.user.company_id.id,
    	readony=True,
        states={'draft': [('readonly', False)]},)
    name = fields.Char(string="Detalle" , required=True,
    	readony=True,
        states={'draft': [('readonly', False)]},)
    date = fields.Date(string="Date", required=True,
    	readony=True,
        states={'draft': [('readonly', False)]},)

    _defaults = {
        'date' : datetime.now(),
        'fecha_inicio': datetime.now().strftime('%Y-%m-%d'),
        'fecha_final': datetime.now().strftime('%Y-%m-%d')
    }

    @api.onchange('fecha_inicio', 'company_id')
    def set_data(self):
        self.name = self.fecha_inicio
        self.fecha_final = self.fecha_inicio
        self.move_ids = self.env['account.move'].search([
            ('document_class_id.sii_code', 'in', [39, 41]),
            ('sended','=', False),
            ('date', '=', self.fecha_inicio),
            ('company_id', '=', self.company_id.id),
            ]).ids
        consumos = self.search_count([
            ('fecha_inicio', '=', self.fecha_inicio),
            ('state', 'not in', ['draft', 'Rechazado']),
            ('company_id', '=', self.company_id.id),
            ])
        if consumos > 0:
            self.correlativo = (consumos+1)

    @api.multi
    def unlink(self):
        for libro in self:
            if libro.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete a Validated book.'))
        return super(ConsumoFolios, self).unlink()

    def split_cert(self, cert):
        certf, j = '', 0
        for i in range(0, 29):
            certf += cert[76 * i:76 * (i + 1)] + '\n'
        return certf

    def create_template_envio(self, RutEmisor, FchResol, NroResol, FchInicio, FchFinal, Correlativo, SecEnvio, EnvioDTE, signature_d, IdEnvio='SetDoc'):
        if Correlativo != 0:
            Correlativo = "<Correlativo>"+Correlativo+"</Correlativo>"
        else:
            Correlativo = ''
        xml = '''<DocumentoConsumoFolios ID="{10}">
<Caratula  version="1.0" >
<RutEmisor>{0}</RutEmisor>
<RutEnvia>{1}</RutEnvia>
<FchResol>{2}</FchResol>
<NroResol>{3}</NroResol>
<FchInicio>{4}</FchInicio>
<FchFinal>{5}</FchFinal>{6}
<SecEnvio>{7}</SecEnvio>
<TmstFirmaEnv>{8}</TmstFirmaEnv>
</Caratula>
{9}
</DocumentoConsumoFolios>
'''.format(RutEmisor, signature_d['subject_serial_number'],
           FchResol, NroResol, FchInicio, FchFinal, str(Correlativo), str(SecEnvio), self.time_stamp(), EnvioDTE,  IdEnvio)
        return xml

    def time_stamp(self, formato='%Y-%m-%dT%H:%M:%S'):
        tz = pytz.timezone('America/Santiago')
        return datetime.now(tz).strftime(formato)

    '''
    Funcion auxiliar para conversion de codificacion de strings
     proyecto experimentos_dte
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2014-12-01
    '''
    def convert_encoding(self, data, new_coding = 'UTF-8'):
        encoding = cchardet.detect(data)['encoding']
        if new_coding.upper() != encoding.upper():
            data = data.decode(encoding, data).encode(new_coding)
        return data

    def xml_validator(self, some_xml_string, validacion='doc'):
        validacion_type = {
            'consu': 'ConsumoFolio_v10.xsd',
            'sig': 'xmldsignature_v10.xsd',
        }
        xsd_file = xsdpath+validacion_type[validacion]
        try:
            xmlschema_doc = etree.parse(xsd_file)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            xml_doc = etree.fromstring(some_xml_string)
            result = xmlschema.validate(xml_doc)
            if not result:
                xmlschema.assert_(xml_doc)
            return result
        except AssertionError as e:
            raise UserError(_('XML Malformed Error:  %s') % e.args)

    '''
    Funcion usada en autenticacion en SII
    Obtencion de la semilla desde el SII.
    Basada en función de ejemplo mostrada en el sitio edreams.cl
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2015-04-01
    '''
    def get_seed(self, company_id):
        #En caso de que haya un problema con la validación de certificado del sii ( por una mala implementación de ellos)
        #esto omite la validacion
        try:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
        url = server_url[company_id.dte_service_provider] + 'CrSeed.jws?WSDL'
        ns = 'urn:'+server_url[company_id.dte_service_provider] + 'CrSeed.jws'
        _server = SOAPProxy(url, ns)
        root = etree.fromstring(_server.getSeed())
        semilla = root[0][0].text
        return semilla

    '''
    Funcion usada en autenticacion en SII
    Creacion de plantilla xml para realizar el envio del token
    Previo a realizar su firma
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def create_template_seed(self, seed):
        xml = u'''<getToken>
<item>
<Semilla>{}</Semilla>
</item>
</getToken>
'''.format(seed)
        return xml

    '''
    Funcion usada en autenticacion en SII
    Creacion de plantilla xml para envolver el Envio de DTEs
    Previo a realizar su firma (2da)
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def create_template_env(self, doc,simplificado=False):
        xsd = 'http://www.sii.cl/SiiDte ConsumoFolio_v10.xsd'
        xml = '''<ConsumoFolios xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="{0}" \
version="1.0">
{1}</ConsumoFolios>'''.format(xsd, doc)
        return xml

    '''
    Funcion usada en autenticacion en SII
    Firma de la semilla utilizando biblioteca signxml
    De autoria de Andrei Kislyuk https://github.com/kislyuk/signxml
    (en este caso particular esta probada la efectividad de la libreria)
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def sign_seed(self, message, privkey, cert):
        doc = etree.fromstring(message)
        signed_node = xmldsig(
            doc, digest_algorithm=u'sha1').sign(
            method=methods.enveloped, algorithm=u'rsa-sha1',
            key=privkey.encode('ascii'),
            cert=cert)
        msg = etree.tostring(
            signed_node, pretty_print=True).replace('ds:', '')
        return msg

    '''
    Funcion usada en autenticacion en SII
    Obtencion del token a partir del envio de la semilla firmada
    Basada en función de ejemplo mostrada en el sitio edreams.cl
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def get_token(self, seed_file,company_id):
        url = server_url[company_id.dte_service_provider] + 'GetTokenFromSeed.jws?WSDL'
        ns = 'urn:'+ server_url[company_id.dte_service_provider] +'GetTokenFromSeed.jws'
        _server = SOAPProxy(url, ns)
        tree = etree.fromstring(seed_file)
        ss = etree.tostring(tree, pretty_print=True, encoding='iso-8859-1')
        respuesta = etree.fromstring(_server.getToken(ss))
        token = respuesta[0][0].text
        return token

    def ensure_str(self,x, encoding="utf-8", none_ok=False):
        if none_ok is True and x is None:
            return x
        if not isinstance(x, str):
            x = x.decode(encoding)
        return x
    def long_to_bytes(self, n, blocksize=0):
        """long_to_bytes(n:long, blocksize:int) : string
        Convert a long integer to a byte string.
        If optional blocksize is given and greater than zero, pad the front of the
        byte string with binary zeros so that the length is a multiple of
        blocksize.
        """
        # after much testing, this algorithm was deemed to be the fastest
        s = b''
        n = long(n)  # noqa
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
        # add back some pad bytes.  this could be done more efficiently w.r.t. the
        # de-padding being done above, but sigh...
        if blocksize > 0 and len(s) % blocksize:
            s = (blocksize - len(s) % blocksize) * b'\000' + s
        return s

    def sign_full_xml(self, message, privkey, cert, uri, type='consu'):
        doc = etree.fromstring(message)
        string = etree.tostring(doc[0])
        mess = etree.tostring(etree.fromstring(string), method="c14n")
        digest = base64.b64encode(self.digest(mess))
        reference_uri='#'+uri
        signed_info = Element("SignedInfo")
        c14n_method = SubElement(signed_info, "CanonicalizationMethod", Algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        sign_method = SubElement(signed_info, "SignatureMethod", Algorithm='http://www.w3.org/2000/09/xmldsig#rsa-sha1')
        reference = SubElement(signed_info, "Reference", URI=reference_uri)
        transforms = SubElement(reference, "Transforms")
        SubElement(transforms, "Transform", Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        digest_method = SubElement(reference, "DigestMethod", Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
        digest_value = SubElement(reference, "DigestValue")
        digest_value.text = digest
        signed_info_c14n = etree.tostring(signed_info,method="c14n",exclusive=False,with_comments=False,inclusive_ns_prefixes=None)
        att = 'xmlns="http://www.w3.org/2000/09/xmldsig#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        #@TODO Find better way to add xmlns:xsi attrib
        signed_info_c14n = signed_info_c14n.replace("<SignedInfo>","<SignedInfo " + att + ">")
        sig_root = Element("Signature",attrib={'xmlns':'http://www.w3.org/2000/09/xmldsig#'})
        sig_root.append(etree.fromstring(signed_info_c14n))
        signature_value = SubElement(sig_root, "SignatureValue")
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        import OpenSSL
        from OpenSSL.crypto import *
        type_ = FILETYPE_PEM
        key=OpenSSL.crypto.load_privatekey(type_,privkey.encode('ascii'))
        signature= OpenSSL.crypto.sign(key,signed_info_c14n,'sha1')
        signature_value.text =textwrap.fill(base64.b64encode(signature),64)
        key_info = SubElement(sig_root, "KeyInfo")
        key_value = SubElement(key_info, "KeyValue")
        rsa_key_value = SubElement(key_value, "RSAKeyValue")
        modulus = SubElement(rsa_key_value, "Modulus")
        key = load_pem_private_key(privkey.encode('ascii'),password=None, backend=default_backend())
        modulus.text =  textwrap.fill(base64.b64encode(self.long_to_bytes(key.public_key().public_numbers().n)),64)
        exponent = SubElement(rsa_key_value, "Exponent")
        exponent.text = self.ensure_str(base64.b64encode(self.long_to_bytes(key.public_key().public_numbers().e)))
        x509_data = SubElement(key_info, "X509Data")
        x509_certificate = SubElement(x509_data, "X509Certificate")
        x509_certificate.text = '\n'+textwrap.fill(cert,64)
        msg = etree.tostring(sig_root)
        msg = msg if self.xml_validator(msg, 'sig') else ''
        fulldoc = message.replace('</ConsumoFolios>',msg+'\n</ConsumoFolios>')
        fulldoc = '<?xml version="1.0" encoding="ISO-8859-1"?>\n'+fulldoc
        fulldoc = fulldoc if self.xml_validator(fulldoc, type) else ''
        return fulldoc

    def get_digital_signature_pem(self, comp_id):
        obj = self.env['res.users'].browse([self.env.user.id])
        if not obj.cert:
            obj = self.env['res.company'].browse([comp_id.id])
            if not obj.cert:
                obj = self.env['res.users'].search(domain=[("authorized_users_ids","=", self.env.user.id)])
            if not obj.cert or not self.env.user.id in obj.authorized_users_ids.ids:
                return False
        signature_data = {
            'subject_name': obj.name,
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert,
            'rut_envia': obj.subject_serial_number
            }
        return signature_data

    def get_digital_signature(self, comp_id):
        obj = self.env['res.users'].browse([self.env.user.id])
        if not obj.cert:
            obj = self.env['res.company'].browse([comp_id.id])
            if not obj.cert:
                obj = self.env['res.users'].search(domain=[("authorized_users_ids","=", self.env.user.id)])
            if not obj.cert or not self.env.user.id in obj.authorized_users_ids.ids:
                return False
        signature_data = {
            'subject_name': obj.name,
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert}
        return signature_data

    '''
    Funcion usada en SII
    Toma los datos referentes a la resolución SII que autoriza a
    emitir DTE
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-06-01
    '''
    def get_resolution_data(self, comp_id):
        resolution_data = {
            'dte_resolution_date': comp_id.dte_resolution_date,
            'dte_resolution_number': comp_id.dte_resolution_number}
        return resolution_data

    @api.multi
    def send_xml_file(self, envio_dte=None, file_name="envio",company_id=False):
        if not company_id.dte_service_provider:
            raise UserError(_("Not Service provider selected!"))

        try:
            signature_d = self.get_digital_signature_pem(
                company_id)
            seed = self.get_seed(company_id)
            template_string = self.create_template_seed(seed)
            seed_firmado = self.sign_seed(
                template_string, signature_d['priv_key'],
                signature_d['cert'])
            token = self.get_token(seed_firmado,company_id)
        except:
            _logger.info(connection_status)
            raise Warning(connection_status)

        url = 'https://palena.sii.cl'
        if company_id.dte_service_provider == 'SIIHOMO':
            url = 'https://maullin.sii.cl'
        post = '/cgi_dte/UPL/DTEUpload'
        headers = {
            'Accept': 'image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, application/vnd.ms-powerpoint, application/ms-excel, application/msword, */*',
            'Accept-Language': 'es-cl',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/4.0 (compatible; PROG 1.0; Windows NT 5.0; YComp 5.0.2.4)',
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
        file_name = file_name + '.xml'
        params['archivo'] = (file_name,envio_dte,"text/xml")
        multi  = urllib3.filepost.encode_multipart_formdata(params)
        headers.update({'Content-Length': '{}'.format(len(multi[0]))})
        response = pool.request_encode_body('POST', url+post, params, headers)
        retorno = {'sii_xml_response': response.data, 'sii_result': 'NoEnviado','sii_send_ident':''}
        if response.status != 200:
            return retorno
        respuesta_dict = xmltodict.parse(response.data)
        if respuesta_dict['RECEPCIONDTE']['STATUS'] != '0':
            _logger.info('l736-status no es 0')
            _logger.info(connection_status[respuesta_dict['RECEPCIONDTE']['STATUS']])
        else:
            retorno.update({'sii_result': 'Enviado','sii_send_ident':respuesta_dict['RECEPCIONDTE']['TRACKID']})
        return retorno

    '''
    Funcion para descargar el xml en el sistema local del usuario
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-05-01
    '''
    @api.multi
    def get_xml_file(self):
        file_name = self.name.replace(' ','_')
        return {
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=account.move.receipt_consumption\
&field=sii_xml_request&id=%s&filename=%s.xml' % (self.id, file_name),
            'target': 'self',
        }

    def format_vat(self, value):
        ''' Se Elimina el 0 para prevenir problemas con el sii, ya que las muestras no las toma si va con
        el 0 , y tambien internamente se generan problemas'''
        if not value or value=='' or value == 0:
            value ="CL666666666"
            #@TODO opción de crear código de cliente en vez de rut genérico
        rut = value[:10] + '-' + value[10:]
        rut = rut.replace('CL0','').replace('CL','')
        return rut

    '''
    Funcion usada en SII
    para firma del timbre (dio errores de firma para el resto de los doc)
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2015-03-01
    '''
    def digest(self, data):
        sha1 = hashlib.new('sha1', data)
        return sha1.digest()

    @api.onchange('fiscal_period','tipo_operacion')
    def _setName(self):
        if self.name:
            return
        self.name = self.tipo_operacion
        if self.fiscal_period:
            self.name += " " + self.fiscal_period

    @api.multi
    def validar_receipt_consumption(self):
        self._validar()
        return self.write({'state': 'NoEnviado'})

    def _acortar_str(self, texto, size=1):
        c = 0
        cadena = ""
        while c < size and c < len(texto):
            cadena += texto[c]
            c += 1
        return cadena

    def _process_imps(self, tax_line_id, totales=0, currency=None, Neto=0, TaxMnt=0, MntExe=0, ivas={}, imp={}):
        mnt = tax_line_id.compute_all(totales,  currency, 1)['taxes'][0]
        if mnt['amount'] < 0:
            mnt['amount'] *= -1
            mnt['base'] *= -1
        if tax_line_id.sii_code in [14, 15, 17, 18, 19, 30,31, 32 ,33, 34, 36, 37, 38, 39, 41, 47, 48]: # diferentes tipos de IVA retenidos o no
            ivas.setdefault(tax_line_id.id, [ tax_line_id, 0])
            ivas[tax_line_id.id][1] += mnt['amount']
            TaxMnt += mnt['amount']
            Neto += mnt['base']
        else:
            imp.setdefault(tax_line_id.id, [tax_line_id, 0])
            imp[tax_line_id.id][1] += mnt['amount']
            if tax_line_id.amount == 0:
                MntExe += mnt['base']
        return Neto, TaxMnt, MntExe, ivas, imp

    def getResumen(self, rec):
        det = collections.OrderedDict()
        det['TpoDoc'] = rec.document_class_id.sii_code
        det['NroDoc'] = int(rec.sii_document_number)
        Neto = 0
        MntExe = 0
        TaxMnt = 0
        tasa = False
        ivas = imp = taxes = {}
        if 'lines' in rec:
            for line in rec.lines:
                if line.tax_ids:
                    for t in line.tax_ids:
                        taxes.setdefault(t.id, [t, 0])
                        taxes[t.id][1] += line.price_subtotal_incl
            for key, t in taxes.iteritems():
                Neto, TaxMnt, MntExe, ivas, imp = self._process_imps(t[0], t[1], rec.pricelist_id.currency_id, Neto, TaxMnt, MntExe, ivas, imp)
        else:  # si la receipt fue hecha por contabilidad
            for l in rec.line_ids:
                if l.tax_line_id:
                    if l.tax_line_id and l.tax_line_id.amount > 0: #supuesto iva único
                        if l.tax_line_id.sii_code in [14, 15, 17, 18, 19, 30,31, 32 ,33, 34, 36, 37, 38, 39, 41, 47, 48]: # diferentes tipos de IVA retenidos o no
                            if not l.tax_line_id.id in ivas:
                                ivas[l.tax_line_id.id] = [l.tax_line_id, 0]
                            if l.credit > 0:
                                ivas[l.tax_line_id.id][1] += l.credit
                            else:
                                ivas[l.tax_line_id.id][1] += l.debit
                        else:
                            if not l.tax_line_id.id in imp:
                                imp[l.tax_line_id.id] = [l.tax_line_id, 0]
                            if l.credit > 0:
                                imp[l.tax_line_id.id][1] += l.credit
                                TaxMnt += l.credit
                            else:
                                imp[l.tax_line_id.id][1] += l.debit
                                TaxMnt += l.debit
                elif l.tax_ids and l.tax_ids[0].amount > 0:
                    if l.credit > 0:
                        Neto += l.credit
                    else:
                        Neto += l.debit
                elif l.tax_ids and l.tax_ids[0].amount == 0: #caso monto exento
                    if l.credit > 0:
                        MntExe += l.credit
                    else:
                        MntExe += l.debit
        if MntExe > 0 :
            det['MntExe'] = int(round(MntExe,0))
        if TaxMnt > 0:
            det['MntIVA'] = int(round(TaxMnt))
            for key, t in ivas.iteritems():
                det['TasaIVA'] = t[0].amount
        amount_total = int(round((Neto + MntExe + TaxMnt), 0))
        det['MntNeto'] = int(round(Neto))
        det['MntTotal'] = amount_total
        return det

    def _last(self, folio, items):# se asumen que vienen ordenados de menor a mayor
        for c in items:
            if folio > c['Final'] and folio > c['Inicial']:
                return c
        return False

    def _nuevo_range(self, folio, f_contrario, contrarios):
        last = self._last(folio, contrarios)#obtengo el último tramo de los contrarios
        if last and last['Inicial'] > f_contrario:
            return True
        return False

    def _orden(self, folio, ranges, contrarios, continuado=True):
        last = self._last(folio, ranges)
        if not continuado or not last or  self._nuevo_range(folio, last['Final'], contrarios):
            r = collections.OrderedDict()
            r['Inicial'] = folio
            r['Final'] = folio
            ranges.append(r)
            return ranges
        result = []
        for r in ranges:
            if r['Final'] == last['Final'] and folio > last['Final']:
                r['Final'] = folio
            result.append(r)
        return result

    def _rangesU(self, resumen, ranges, continuado=True):
        if not ranges:
            ranges = collections.OrderedDict()
        folio = resumen['NroDoc']
        if 'A' in resumen:
            utilizados = ranges['itemUtilizados'] if 'itemUtilizados' in ranges else []
            if not 'itemAnulados' in ranges:
                ranges['itemAnulados'] = []
                r = collections.OrderedDict()
                r['Inicial'] = folio
                r['Final'] = folio
                ranges['itemAnulados'].append(r)
            else:
                ranges['itemAnulados'] = self._orden(resumen['NroDoc'], ranges['itemAnulados'], utilizados, continuado)
                return ranges
        anulados = ranges['itemAnulados'] if 'itemAnulados' in ranges else []
        if not 'itemUtilizados' in ranges:
            ranges['itemUtilizados'] = []
            r = collections.OrderedDict()
            r['Inicial'] = folio
            r['Final'] = folio
            ranges['itemUtilizados'].append(r)
        else:
            ranges['itemUtilizados'] = self._orden(resumen['NroDoc'], ranges['itemUtilizados'], anulados, continuado)
        return ranges

    def _setResumen(self,resumen,resumenP,continuado=True):
        resumenP['TipoDocumento'] = resumen['TpoDoc']
        if 'MntNeto' in resumen and not 'MntNeto' in resumenP:
            resumenP['MntNeto'] = resumen['MntNeto']
        elif 'MntNeto' in resumen:
            resumenP['MntNeto'] += resumen['MntNeto']
        elif not 'MntNeto' in resumenP:
            resumenP['MntNeto'] = 0
        if 'MntIVA' in resumen and not 'MntIva' in resumenP:
            resumenP['MntIva'] = resumen['MntIVA']
        elif 'MntIVA' in resumen:
            resumenP['MntIva'] += resumen['MntIVA']
        elif not 'MntIva' in resumenP:
            resumenP['MntIva'] = 0
        if 'TasaIVA' in resumen and not 'TasaIVA' in resumenP:
            resumenP['TasaIVA'] = resumen['TasaIVA']
        if 'MntExe' in resumen and not 'MntExento' in resumenP:
            resumenP['MntExento'] = resumen['MntExe']
        elif 'MntExe' in resumen:
            resumenP['MntExento'] += resumen['MntExe']
        elif not 'MntExento' in resumenP:
            resumenP['MntExento'] = 0
        if not 'MntTotal' in resumenP:
            resumenP['MntTotal'] = resumen['MntTotal']
        else:
            resumenP['MntTotal'] += resumen['MntTotal']
        if 'FoliosEmitidos' in resumenP:
            resumenP['FoliosEmitidos'] +=1
        else:
            resumenP['FoliosEmitidos'] = 1

        if not 'FoliosAnulados' in resumenP:
            resumenP['FoliosAnulados'] = 0
        if 'Anulado' in resumen : # opción de indiar de que está anulado por panel SII no por nota
            resumenP['FoliosAnulados'] += 1
        elif 'FoliosUtilizados' in resumenP:
            resumenP['FoliosUtilizados'] += 1
        else:
            resumenP['FoliosUtilizados'] = 1
        if not str(resumen['TpoDoc'])+'_folios' in resumenP:
            resumenP[str(resumen['TpoDoc'])+'_folios'] = collections.OrderedDict()
        resumenP[str(resumen['TpoDoc'])+'_folios'] = self._rangesU(resumen, resumenP[str(resumen['TpoDoc'])+'_folios'], continuado)
        return resumenP

    def _validar(self):
        dicttoxml.set_debug(False)
        cant_doc_batch = 0
        company_id = self.company_id
        dte_service = company_id.dte_service_provider
        try:
            signature_d = self.get_digital_signature(company_id)
        except:
            raise Warning(_('''There is no Signer Person with an \
        authorized signature for you in the system. Please make sure that \
        'user_signature_key' module has been installed and enable a digital \
        signature, for you or make the signer to authorize you to use his \
        signature.'''))
        certp = signature_d['cert'].replace(
            BC, '').replace(EC, '').replace('\n', '')
        resumenes = {}
        TpoDocs = []
        orders = []
        recs = sorted(self.with_context(lang='es_CL').move_ids, key=lambda t: t.sii_document_number)
        for rec in recs:
            document_class_id = rec.document_class_id if 'document_class_id' in rec else rec.sii_document_class_id
            if not document_class_id or document_class_id.sii_code not in [39, 41, 61]:
                _logger.info("Por este medio solamente e pueden declarar receipts o Notas de crédito Electrónicas, por favor elimine el documento %s del listado" % rec.name)
                continue
            rec.sended = True
            if not rec.sii_document_number:
                orders += self.env['pos.order'].search(
                        [('account_move', '=', rec.id),
                         ('invoice_id' , '=', False),
                         ('sii_document_number', 'not in', [False, '0']),
                         ('document_class_id.sii_code', 'in', [39, 41, 61]),
                        ]).ids
            else:
                resumen = self.getResumen(rec)
                TpoDoc = resumen['TpoDoc']
                TpoDocs.append(TpoDoc)
                if not TpoDoc in resumenes:
                    resumenes[TpoDoc] = collections.OrderedDict()
                resumenes[TpoDoc] = self._setResumen(resumen, resumenes[TpoDoc])
        if orders:
            orders_array = sorted(self.env['pos.order'].browse(orders).with_context(lang='es_CL'), key=lambda t: t.sii_document_number)
            ant = 0
            for order in orders_array:
                resumen = self.getResumen(order)
                TpoDoc = resumen['TpoDoc']
                TpoDocs.append(TpoDoc)
                if not TpoDoc in resumenes:
                    resumenes[TpoDoc] = collections.OrderedDict()
                resumenes[TpoDoc] = self._setResumen(resumen, resumenes[TpoDoc],((ant+1) == order.sii_document_number))
                ant = order.sii_document_number
        Resumen=[]
        for r, value in resumenes.iteritems():
            _logger.info(value)
            if str(r)+'_folios' in value:
                folios = value[ str(r)+'_folios' ]
                if 'itemUtilizados' in folios:
                    for range in folios['itemUtilizados']:
                        utilizados = []
                        utilizados.append({'RangoUtilizados': range})
                    folios['itemUtilizados'] = utilizados
                if 'itemAnulados' in folios:
                    for range in folios['itemAnulados']:
                        anulados = []
                        anulados.append({'RangoAnulados': range})
                    folios['itemAnulados'] = anulados
                value[ str(r)+'_folios' ] = folios
            Resumen.extend([ {'Resumen':value}])
        dte = collections.OrderedDict({'item':Resumen})
        resol_data = self.get_resolution_data(company_id)
        RUTEmisor = self.format_vat(company_id.vat)
        RUTRecep = "60803000-K" # RUT SII
        xml = dicttoxml.dicttoxml(
            dte, root=False, attr_type=False)
        doc_id =  'CF_'+self.date
        Correlativo = self.correlativo
        SecEnvio = self.sec_envio
        cf = self.create_template_envio( RUTEmisor,
            resol_data['dte_resolution_date'],
            resol_data['dte_resolution_number'],
            FchInicio, FchFinal, Correlativo, SecEnvio,
            xml, signature_d, doc_id)
        xml  = self.create_template_env(cf)
        root = etree.XML( xml )
        xml_pret = etree.tostring(root, pretty_print=True)\
                .replace('<item>','\n').replace('</item>','')\
                .replace('<itemNoRec>','').replace('</itemNoRec>','\n')\
                .replace('<itemOtrosImp>','').replace('</itemOtrosImp>','\n')\
                .replace('<itemUtilizados>','').replace('</itemUtilizados>','\n')\
                .replace('<itemAnulados>','').replace('</itemAnulados>','\n')
        for TpoDoc in TpoDocs:
        	xml_pret = xml_pret.replace('<key name="'+str(TpoDoc)+'_folios">','').replace('</key>','\n').replace('<key name="'+str(TpoDoc)+'_folios"/>','\n')
        _logger.info(xml_pret)
        envio_dte = self.convert_encoding(xml_pret, 'ISO-8859-1')
        envio_dte = self.sign_full_xml(
            envio_dte, signature_d['priv_key'], certp,
            doc_id, 'consu')
        doc_id += '.xml'
        self.sii_xml_request = envio_dte
        #self.send_file_name = doc_id
        return envio_dte, doc_id

    @api.multi
    def do_dte_send_receipt_consumption(self):
        if self.state not in ['NoEnviado', 'Rechazado']:
            raise UserError("El Libro  ya ha sido enviado")
        envio_dte, doc_id =  self._validar()
        company_id = self.company_id
        result = self.send_xml_file(envio_dte, doc_id, company_id)
        self.write({
            'sii_xml_response':result['sii_xml_response'],
            'sii_send_ident':result['sii_send_ident'],
            'state': result['sii_result'],
            'sii_xml_request':envio_dte
            })

    def _get_send_status(self, track_id, signature_d,token):
        url = server_url[self.company_id.dte_service_provider] + 'QueryEstUp.jws?WSDL'
        ns = 'urn:'+ server_url[self.company_id.dte_service_provider] + 'QueryEstUp.jws'
        _server = SOAPProxy(url, ns)
        respuesta = _server.getEstUp(self.company_id.vat[2:-1],self.company_id.vat[-1],track_id,token)
        self.sii_message = respuesta
        resp = xmltodict.parse(respuesta)
        _logger.info(respuesta)
        status = False
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "-11":
            status =  {'warning':{'title':_('Error -11'), 'message': _("Error -11: Espere a que sea aceptado por el SII, intente en 5s más")}}
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "EPR":
            self.state = "Proceso"
            if 'SII:RESP_BODY' in resp['SII:RESPUESTA'] and resp['SII:RESPUESTA']['SII:RESP_BODY']['RECHAZADOS'] == "1":
                self.sii_result = "Rechazado"
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "RCT":
            self.state = "Rechazado"
            status = {'warning':{'title':_('Error RCT'), 'message': _(resp['SII:RESPUESTA']['GLOSA'])}}
        return status

    def _get_dte_status(self, signature_d, token):
        url = server_url[self.company_id.dte_service_provider] + 'QueryEstDte.jws?WSDL'
        ns = 'urn:'+ server_url[self.company_id.dte_service_provider] + 'QueryEstDte.jws'
        _server = SOAPProxy(url, ns)
        receptor = self.format_vat(self.partner_id.vat)
        date = datetime.strptime(self.date, "%Y-%m-%d").strftime("%d-%m-%Y")
        respuesta = _server.getEstDte(signature_d['subject_serial_number'][:8], str(signature_d['subject_serial_number'][-1]),
                self.company_id.vat[2:-1],self.company_id.vat[-1], receptor[:8],receptor[2:-1],str(self.document_class_id.sii_code), str(self.sii_document_number),
                date, str(self.amount_total),token)
        self.sii_message = respuesta
        resp = xmltodict.parse(respuesta)
        _logger.info(resp)
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == '2':
            status = {'warning':{'title':_("Error code: 2"), 'message': _(resp['SII:RESPUESTA']['SII:RESP_HDR']['GLOSA'])}}
            return status
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "EPR":
            self.state = "Proceso"
            if 'SII:RESP_BODY' in resp['SII:RESPUESTA'] and resp['SII:RESPUESTA']['SII:RESP_BODY']['RECHAZADOS'] == "1":
                self.state = "Rechazado"
            if resp['SII:RESPUESTA']['SII:RESP_BODY']['REPARO'] == "1":
                self.state = "Reparo"
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "RCT":
            self.state = "Rechazado"

    @api.multi
    def ask_for_dte_status(self):
        try:
            signature_d = self.get_digital_signature_pem(
                self.company_id)
            seed = self.get_seed(self.company_id)
            template_string = self.create_template_seed(seed)
            seed_firmado = self.sign_seed(
                template_string, signature_d['priv_key'],
                signature_d['cert'])
            token = self.get_token(seed_firmado,self.company_id)
        except:
            raise Warning(connection_status[response.e])
        xml_response = xmltodict.parse(self.sii_xml_response)
        if self.state == 'Enviado':
            status = self._get_send_status(self.sii_send_ident, signature_d, token)
            if self.state != 'Proceso':
                return status
