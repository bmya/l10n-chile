# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class SendDteMulti(models.TransientModel):
    _name = 'sii.dte.build.sales.book.wizard'
    _description = 'SII Build Sales Book'

    @api.model
    def _getIDs(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        return self.env['account.move'].browse(active_ids)
    @api.model
    def _getCompany(self):
        return self.company_id.id
        
    company_id = fields.Many2one('res.company', default=_getCompany)
    move_ids = fields.Many2many('account.move', string="Moves", default=_getIDs)

    @api.multi
    def confirm(self):
        data = {
                'move_ids': self.move_ids,
                'tipo_report': 'special',
                'tipo_operacion': 'purchase',
                'tipo_envio': 'total',
                'folio_notificacion': 612124,
                'fiscal_period': '2016-07',
                'company_id':self.company_id.id, }
        libro = self.env['account.move.ledger'].create(data)
        libro.write(data)
        libro.do_dte_send_report()

