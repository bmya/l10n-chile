# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import except_orm, UserError
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    responsability_id = fields.Many2one(
        'sii.responsability', 'Responsability')
    document_type_id = fields.Many2one(
        'sii.document_type', 'Document type')
    start_date = fields.Date('Start-up Date')
    tp_sii_code = fields.Char(
        'Tax Payer SII Code', readonly=True)

    # @api.onchange('document_type_id')
    # def _onchange_doc_type(self):
    #     raise UserError('oooooo')

    @api.onchange('responsability_id', 'document_type_id')
    def _onchange_resp(self):
        res_exid = ['dt_RUT', 'dt_RUN']
        ext_exid = ['dt_CIe', 'res_EXT']
        res_ids = map(lambda z: self.env.ref('l10n_cl_invoice.'+z).id, res_exid)
        ext_ids = map(lambda z: self.env.ref('l10n_cl_invoice.'+z).id, ext_exid)
        doc_ids = self.env['sii.document_type'].search(
            [('default_doc_num', '!=', False)])
        default_docs = set([doc_id.default_doc_num for doc_id in doc_ids])
        _logger.info(self.document_type_id.id)
        if self.document_type_id.id in res_ids:
            _logger.info('el tipo de documento es de residente')
            if self.document_number in default_docs:
                self.document_number = False
            if self.responsability_id == self.env.ref(
                    'l10n_cl_invoice.res_EXT'):
                self.responsability_id = False
        elif self.document_type_id.id in ext_ids:
            _logger.info('el tipo de documento es de extranjero')
            self.document_number = self.document_type_id.default_doc_num
            self.responsability_id = self.env.ref('l10n_cl_invoice.res_EXT')
        elif self.document_type_id.id == self.env.ref(
                    'l10n_cl_invoice.dt_Sigd').id:
            _logger.info('el tipo de documento es sin identificar')
            self.document_number = self.document_type_id.default_doc_num
            self.responsability_id = self.env.ref('l10n_cl_invoice.res_CF')
