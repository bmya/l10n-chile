# -*- coding: utf-8 -*-
from openerp.addons.report_xlsx.report.report_xlsx import ReportXlsx


class PartnerXlsx(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, libro):
        for obj in libro:
            report_name = obj.name
            # One sheet by partner
            sheet = workbook.add_worksheet(report_name[:31])
            bold = workbook.add_format({'bold': True})
            sheet.write(0, 0, obj.name, bold)
            sheet.write(0, 1, obj.company_id.name, bold)
            sheet.write(0, 2, obj.periodo_tributario, bold)
            sheet.write(0, 3, obj.tipo_operacion, bold)
            sheet.write(0, 4, obj.tipo_libro, bold)
            sheet.write(0, 5, obj.tipo_operacion, bold)
            sheet.write(2, 0, u"Fecha", bold)
            sheet.write(2, 1, u"Número", bold)
            sheet.write(2, 2, u"Tipo de Identificación", bold)
            sheet.write(2, 3, u"Número de Documento", bold)
            sheet.write(2, 4, u"Compañia", bold)
            sheet.write(2, 5, u"Referencia", bold)
            sheet.write(2, 6, u"Total", bold)
            line = 3
            for rec in libro.move_ids:
                sheet.write(line, 0, rec.date, bold)
                sheet.write(line, 1, rec.document_number, bold)
                sheet.write(line, 2, rec.document_class_id.name, bold)
                sheet.write(line, 3, rec.sii_document_number, bold)
                sheet.write(line, 4, rec.partner_id.name, bold)
                sheet.write(line, 5, rec.ref, bold)
                sheet.write(line, 6, rec.amount, bold)
                line += 1


PartnerXlsx('report.account.move.book.xlsx',
            'account.move.book')
