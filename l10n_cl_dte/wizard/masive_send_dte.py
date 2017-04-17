# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class SendDteWizardMulti(models.TransientModel):
    _name = 'sii.dte.masive_send.wizard'
    _description = 'SII Masive send Wizard'

    @api.model
    def _get_ids(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        return [(6, 0, active_ids)]

    documentos = fields.Many2many(
        'account.invoice', string="Movimientos", default=_get_ids)

    att_number = fields.Char(string="Número de atención")

    @api.multi
    def confirm(self):
        self.documentos.do_dte_send_invoice(self.att_number)
        return UserError("Enviado")
