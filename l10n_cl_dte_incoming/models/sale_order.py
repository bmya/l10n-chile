# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment = fields.Text('Payment Term')  # <- JSON payment
    document_type = fields.Integer('Document Type')  # <- sii.inc.dte.TipoDoc
    document_number = fields.Integer('Document Number')  # <- sii.inc.dte.Folio

# dte_email = fields.Char('DTE Email', related='partner_id.dte_email')