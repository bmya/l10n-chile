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
    _inherit = 'account.invoice'



class LibreDte():
    _inherit = 'account.invoice'



class PySIIDTE():
    _inherit = 'account.invoice'

