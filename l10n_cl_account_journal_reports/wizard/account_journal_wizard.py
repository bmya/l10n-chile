# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from dateutil.relativedelta import relativedelta
import xmltodict
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class AccountJournalBookWizard(models.TransientModel):
    _name = 'account.journal.sheet.report'
    _inherit = 'account.common.journal.report'
    _description = 'Journal Book Report Wizard'

    journal_ids = fields.Many2many(
        'account.journal',
        'account_journal_book_journal_rel',
        'acc_journal_entries_id',
        'journal_id',
        'Journals',
        required=True,
        ondelete='cascade',
    )
    last_entry_number = fields.Integer(
        string='Último número de asiento',
        required=True,
        default=0,
    )
    date_from = fields.Date(
        required=True,
    )
    date_to = fields.Date(
        required=True,
    )

    # target_move = fields.Char('Target Move')  # definido por mi para evitar error
    # company_id = fields.Many2one('Company')

    # @api.onchange('company_id')
    # def _onchange_company_id(self):
    #     dates = self.company_id.compute_fiscalyear_dates(
    #         fields.Date.from_string(fields.Date.today()))
    #     if dates:
    #         self.date_from = dates['date_from']
    #         self.date_to = dates['date_to']

    @api.multi
    def _print_report(self, data):
        date_from = fields.Date.from_string(self.date_from)
        date_to = fields.Date.from_string(self.date_to)
        periods = []
        dt_from = date_from.replace(day=1)
        while dt_from < date_to:
            dt_to = dt_from + relativedelta(months=1, days=-1)
            periods.append((fields.Date.to_string(dt_from),
                            fields.Date.to_string(dt_to)))
            # este va a se la date from del proximo
            dt_from = dt_to + relativedelta(days=1)
        domain = [('company_id', '=', self.company_id.id)]
        if self.target_move == 'posted':
            domain.append(('state', '=', 'posted'))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<', self.date_to))
        moves = self.env['account.move'].search(domain)
        """
        para 10.0:
        return self.env['report'].with_context(
            periods=periods,
            last_entry_number=self.last_entry_number,
        ).get_action(
            moves, 'journal_book_pdf_view_pdf')
        """
        data['ids'] = moves.ids
        data['model'] = 'account.move'
        _logger.info('\n\n\n\n\nperiods: %s, last_entry_number: %s, data: %s' % (periods, self.last_entry_number, data))
        return self.env.ref('l10n_cl_account_journal_reports.journal_book_pdf_view_pdf_menu').with_context(
            periods=periods,
            last_entry_number=self.last_entry_number,
        ).report_action(moves, data=data)

    def _print_report_xlsx(self, data):
        date_from = fields.Date.from_string(self.date_from)
        date_to = fields.Date.from_string(self.date_to)
        periods = []
        dt_from = date_from.replace(day=1)
        while dt_from < date_to:
            dt_to = dt_from + relativedelta(months=1, days=-1)
            periods.append((fields.Date.to_string(dt_from),
                            fields.Date.to_string(dt_to)))
            dt_from = dt_to + relativedelta(days=1)
        domain = [('company_id', '=', self.company_id.id)]
        if self.target_move == 'posted':
            domain.append(('state', '=', 'posted'))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<', self.date_to))
        records = self.env['account.move'].search(domain, order='journal_id, date, id')
        data['ids'] = records.ids
        data['model'] = 'account.move'
        _logger.info(
            '\n\n\n\n\n Periods: %s, last_entry_number: %s, data: %s' % (periods, self.last_entry_number, data))
        # return self.env.ref(
        #     'l10n_cl_account_journal_reports.account_journal_book_xlsx').report_action(records, data=data)

        return self.env['report'].get_action(
            records, 'l10n_cl_account_journal_reports.  journal_xlsx', data=data)


    @api.multi
    def check_report_xlsx(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', []),
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move'])[0]
        # used_context = self._build_contexts(data)
        # data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        return self._print_report_xlsx(data)


class JournalXlsx(models.AbstractModel):
    _name = "report.journal_xlsx"
    # _inherit = 'report.report_xlsx.abstract'

    @staticmethod
    def generate_xlsx_report(workbook, data, records):
        _logger.info('data: %s, records: %s' % (data, records))
        report_name = 'Libro Diario'
        sheet = workbook.add_worksheet(report_name[:31])
        bold = bold1 = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': 'silver',
            'border': 1,
        })
        center = workbook.add_format({
            'align': 'center',
        })
        # sheet.set_column(0, 15, 18)

        sheet.merge_range('A1:F1', "LIBRO DIARIO", bold)
        sheet.merge_range('A3:B3', "Nombre o Razón Social", bold)
        sheet.merge_range('A4:B4', "Rol Único Tributario", bold)
        sheet.merge_range('A5:B5', "Fecha Inicial", bold)
        # sheet.merge_range('A6:B6', "Periodo Tributario", bold)

        sheet.merge_range('C3:F3', records[0].company_id.name, bold)
        sheet.merge_range('C4:F4', records[0].company_id.main_id_number, bold)
        date_emision = records[0].date[8:] + '-' + records[0].date[5:7] + '-' + records[0].date[:4]
        sheet.merge_range('C5:F5', date_emision, bold)
        # # sheet.merge_range('C6:D6', obj.fiscal_period, center)

        cell_format = workbook.add_format()
        entry_format = workbook.add_format({
            'bg_color': '#e6e6e6',
        })
        bold = workbook.add_format({'bold': True})

        row = 5

        journal = ''
        for obj in records:
            row += 3
            if journal != obj.journal_id.name:
                sheet.merge_range('A{0}:F{0}'.format(row), "DIARIO: %s" % obj.journal_id.name, bold1)
                row += 1
                sheet.write(row, 0, 'Cod. Cta', bold)
                sheet.write(row, 1, 'Cta', bold)
                sheet.write(row, 2, 'Glosa', bold)
                sheet.write(row, 3, 'Ctro. Costos', bold)
                sheet.write(row, 4, 'Débito', bold)
                sheet.write(row, 5, 'Crédito', bold)
                journal = obj.journal_id.name
                row += 1

            date_day = obj.date[8:] + '-' + obj.date[5:7] + '-' + obj.date[:4]
            sheet.write(row, 0, date_day, entry_format)
            sheet.write(row, 1, obj.name, entry_format)
            if obj.ref:
                sheet.write(row, 2, obj.ref, entry_format)
            else:
                sheet.write(row, 2, '', entry_format)
            if obj.document_type_id.doc_code_prefix and obj.document_number:
                sheet.write(
                    row, 3, 'Ref: %s %s' % (
                        obj.document_type_id.doc_code_prefix, obj.document_number), entry_format)
            else:
                sheet.write(row, 3, '', entry_format)
            sheet.write(row, 4, '', entry_format)
            sheet.write(row, 5, '', entry_format)
            for l in obj.line_ids:
                row += 1
                sheet.write(row, 0, l.account_id.code, cell_format)
                sheet.write(row, 1, l.account_id.name, cell_format)
                if l.name:
                    sheet.write(row, 2, l.name, cell_format)
                else:
                    sheet.write(row, 2, '', cell_format)
                if l.analytic_account_id.name:
                    sheet.write(row, 3, l.analytic_account_id.name, cell_format)
                else:
                    sheet.write(row, 3, '', cell_format)
                sheet.write_number(row, 4, l.debit, cell_format)
                sheet.write_number(row, 5, l.credit, cell_format)
