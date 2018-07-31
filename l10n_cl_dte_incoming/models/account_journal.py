# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging


_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Sales Analytic Account')

    def assign_analytic_account(self):
        """
        Función que permite asignar a los asientos contables la cuenta analitica que corresponde
        al diario (orientado a diario de ventas y para el proyecto bfs)
        :return:
        """
        account_move_obj = self.env['account.move']
        account_invoice_obj = self.env['account.invoice']
        account_move_ids = account_move_obj.search([('journal_id', '=', self.id)])
        for account_move in account_move_ids:
            for line_id in account_move.line_ids:
                if not line_id.analytic_account_id:
                    line_id.analytic_account_id = self.analytic_account_id
        account_invoice_ids = account_invoice_obj.search([('journal_id', '=', self.id)])
        for account_invoice in account_invoice_ids:
            for line_id in account_invoice.invoice_line_ids:
                if not line_id.account_analytic_id:
                    line_id.account_analytic_id = self.analytic_account_id


