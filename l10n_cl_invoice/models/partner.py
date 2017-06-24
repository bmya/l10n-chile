# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import except_orm, UserError
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'

    responsability_id = fields.Many2one(
        'sii.responsability', 'Responsability')
    document_type_id = fields.Many2one(
        'sii.document_type', 'Document type')
    start_date = fields.Date('Start-up Date')
    tp_sii_code = fields.Char(
        'Tax Payer SII Code', compute='_get_tp_sii_code', readonly=True)

    @api.multi
    @api.onchange('responsability_id')
    def _get_tp_sii_code(self):
        for record in self:
            record.tp_sii_code = str(record.responsability_id.tp_sii_code)

    # @api.onchange('document_number', 'document_type_id')
    # def onchange_document(self):
    #     clean_vat = (re.sub('[^1234567890Kk]', '',
    #                         str(self.document_number))).zfill(9).upper()
    #     formatted_vat = '%s.%s.%s-%s' % (
    #         clean_vat[0:2], clean_vat[2:5], clean_vat[5:8], clean_vat[-1])
    #     if self.document_number and (
    #                     self.document_type_id.id == self.env.ref(
    #                     'l10n_cl_invoice.dt_RUT').id or
    #                         self.document_type_id.id == self.env.ref(
    #                     'l10n_cl_invoice.dt_RUN').id):
    #         pass
    #     elif self.document_number and \
    #         self.document_type_id.id == self.env.ref(
    #                 'l10n_cl_invoice.dt_Sigd').id:
    #         formatted_vat = '66.666.666-6'
    #         clean_vat = '666666666'
    #     else:
    #         formatted_vat = '55.555.555-5'
    #         clean_vat = '555555555'
    #     if self.document_number != formatted_vat:
    #         self.document_number = formatted_vat
    #     if self.vat != 'CL%s' % clean_vat:
    #         self.vat = 'CL%s' % clean_vat
