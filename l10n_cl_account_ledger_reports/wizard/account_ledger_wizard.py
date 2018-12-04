# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from dateutil.relativedelta import relativedelta
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
import xmltodict
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class AccountJournalBookWizard(models.TransientModel):
    _name = "account.report.general.ledger"
    _inherit = "account.report.general.ledger"

    from_account = fields.Char("To Account")
    to_account = fields.Char("To Account")

    @api.multi
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['from_account', 'to_account'])[0])
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('account.action_report_general_ledger').with_context(
            landscape=True).report_action(records, data=data)
