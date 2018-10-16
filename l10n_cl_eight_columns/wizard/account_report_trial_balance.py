# -*- encoding: utf-8 -*-
import logging

from odoo import api, models
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
from odoo.addons.web.controllers import main as report
from odoo.http import content_disposition, request, route

_logger = logging.getLogger(__name__)


class AccountBalanceReport(models.TransientModel):
    _inherit = 'account.balance.report'

    @api.multi
    def check_report_xlsx(self):
        self.ensure_one()
        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(['date_from', 'date_to', 'journal_ids', 'target_move'])[0],
        }
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        return self._print_report_xlsx(data)

    def _print_report_xlsx(self, data):
        data = self.pre_print_report(data)
        records = self.env[data['model']].browse(data.get('ids', []))

        return self.env['report'].get_action(records, 'trialbalance_xlsx', data=data)


class ReportXLSXTrialBalance(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, records):
        
        active_model = self.env.context.get('active_model', 'ir.ui.menu')

        datas = {}
        datas['form'] = records.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'display_account'])[0]
        used_context = records._build_contexts(datas)
        datas['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        display_account = datas['form'].get('display_account')
        accounts = docs if self.model == 'account.account' else self.env['account.account'].search([])
        
        display_account = datas['form'].get('display_account')
        
        report_model = self.env['report.account.report_trialbalance']
        account_res = report_model.with_context(datas['form'].get('used_context'))._get_accounts(accounts, display_account)


        report_name = 'Prueba'

        xls_header = [
            "Codigo",
            "Cuenta",
            "Debitos",
            "Creditos",
            "Deudor",
            "Acreedor",
            "Activo",
            "Pasivo",
            "Perdida",
            "Ganancia",
        ]

        cell_format = workbook.add_format()

        bold = workbook.add_format({'bold': True})

        sheet = workbook.add_worksheet()
        cols, rows = 0, 0

        for col in xls_header:
            sheet.write(rows, cols, col, bold)
            cols += 1
            sheet.set_column(rows, cols, 25)

        total_debito = 0
        total_credito = 0
        total_deudor = 0
        total_acreedor = 0
        total_activo = 0
        total_pasivo = 0
        total_perdida = 0
        total_ganancia = 0

        rows = range(1, len(account_res)+1)
        for row, account in zip(rows, account_res):

            sheet.write(row, 0, account["code"])
            sheet.write(row, 1, account["name"])

            if account["debit"] > 0:
                total_debito += account["debit"]
                sheet.write(row, 2, account["debit"])

            if account["credit"] > 0:
                total_credito += account["credit"]
                sheet.write(row, 3, account["credit"])

            deudor = acreedor = activo = pasivo = perdida = ganancia = 0

            if account["balance"] > 0:
                deudor = account['balance']
                total_deudor += deudor
                sheet.write(row, 4, deudor)
            elif account["balance"] < 0:
                acreedor = account['balance']
                total_acreedor += acreedor
                sheet.write(row, 5, abs(acreedor))

            if account["code"].startswith(('1','2','3','9')):
                if account["balance"] > 0:
                    activo = account['balance']
                    total_activo += activo
                    sheet.write(row, 6, activo)
                elif account["balance"] < 0:
                    pasivo = account['balance']
                    total_pasivo += pasivo
                    sheet.write(row, 7, abs(pasivo))

            if account["code"].startswith(('4','5','6')):
                if account["balance"] > 0:
                    perdida = account['balance']
                    total_perdida += perdida
                    sheet.write(row, 8, perdida)
                elif account["balance"] < 0:
                    ganancia = account['balance']
                    total_ganancia += ganancia
                    sheet.write(row, 9, abs(ganancia))

        #SUMAS
        sum_row = rows[-1] + 1
        sheet.write(sum_row, 2, total_debito, bold)
        sheet.write(sum_row, 3, total_credito, bold)
        sheet.write(sum_row, 4, total_deudor, bold)
        sheet.write(sum_row, 5, abs(total_acreedor), bold)
        sheet.write(sum_row, 6, total_activo, bold)
        sheet.write(sum_row, 7, abs(total_pasivo), bold)
        sheet.write(sum_row, 8, total_perdida, bold)
        sheet.write(sum_row, 9, abs(total_ganancia), bold)

        #RESULTADOS
        res_row = sum_row + 1

        dif_act_pas = total_activo - abs(total_pasivo)
        if dif_act_pas < 0:
            sheet.write(res_row, 6, abs(dif_act_pas), bold)
        elif dif_act_pas > 0:
            sheet.write(res_row, 7, dif_act_pas, bold)

        dif_per_gan = total_perdida - abs(total_ganancia)
        if dif_per_gan < 0:
            sheet.write(res_row, 8, abs(dif_per_gan), bold)
        elif dif_per_gan > 0:
            sheet.write(res_row, 9, dif_per_gan, bold)

ReportXLSXTrialBalance('report.trialbalance_xlsx', 'account.balance.report')