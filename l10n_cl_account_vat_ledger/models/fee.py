# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import dateutil.relativedelta as relativedelta
import logging
_logger = logging.getLogger(__name__)


class Fees(models.Model):
    _name = 'account.move.book.fees'

    tipo_report = fields.Selection([
                ('ANUAL','Anual'),
                ('monthly','Mensual'),
                ],
                string="Tipo de Libro",
                default='monthly',
                required=True,
                readonly=True,
                states={'draft': [('readonly', False)]}
            )
    fiscal_period = fields.Char(
        string='Periodo Tributario',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company',
        string="Compañía",
        required=True,
        default=lambda self: self.env.user.company_id.id,
        readonly=True,
        states={'draft': [('readonly', False)]})
    name = fields.Char(
        string="Detalle",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Válido'),
        ],
        default="draft",
        string="Estado")
    move_ids = fields.Many2many('account.move',
        readonly=True,
        states={'draft': [('readonly', False)]})
    taxes = fields.One2many('account.move.book.fees.tax',
        'book_id',
        string="Detalle Impuestos")

    _defaults = {
        'date' : datetime.now(),
        'fiscal_period': datetime.now().strftime('%Y-%m'),
    }

    @api.onchange('fiscal_period','tipo_report')
    def _setName(self):
        self.name = self.tipo_report
        if self.fiscal_period:
            self.name += " " + self.fiscal_period

    @api.onchange('fiscal_period', 'company_id')
    def set_movimientos(self):
        current = datetime.strptime( self.fiscal_period + '-01', '%Y-%m-%d' )
        next_month = current + relativedelta.relativedelta(months=1)
        query = [
            ('company_id', '=', self.company_id.id),
            ('sended', '=', False),
            ('date' , '<', next_month.strftime('%Y-%m-%d')),
            ('document_class_id.sii_code', 'in', [70, 71]),
            ]
        four_month = current + relativedelta.relativedelta(months=-4)
        query.append(('date' , '>=', four_month.strftime('%Y-%m-%d')))
        domain = 'purchase'
        query.append(('journal_id.type', '=', domain))
        self.move_ids = self.env['account.move'].search(query)

    @api.onchange('move_ids')
    def compute_taxes(self):
        imp = {}
        for move in self.move_ids:
            for l in move.line_ids:
                if l.tax_line_id:
                    if l.tax_line_id:
                        if not l.tax_line_id.id in imp:
                            imp[l.tax_line_id.id] = {'tax_id':l.tax_line_id.id, 'credit':0 , 'debit': 0,}
                        imp[l.tax_line_id.id]['credit'] += l.credit
                        imp[l.tax_line_id.id]['debit'] += l.debit
                        if l.tax_line_id.activo_fijo:
                            ActivoFijo[1] += l.credit
                elif l.tax_ids and l.tax_ids[0].amount == 0: #caso monto exento
                    if not l.tax_ids[0].id in imp:
                        imp[l.tax_ids[0].id] = {'tax_id':l.tax_ids[0].id, 'credit':0 , 'debit': 0,}
                    imp[l.tax_ids[0].id]['credit'] += l.credit
                    imp[l.tax_ids[0].id]['debit'] += l.debit
        if self.taxes and isinstance(self.id, int):
            self._cr.execute("DELETE FROM account_move_book_tax WHERE book_id=%s", (self.id,))
            self.invalidate_cache()
        lines = [[5,],]
        for key, i in imp.items():
            i['currency_id'] = self.env.user.company_id.currency_id.id
            lines.append([0,0, i])
        self.taxes = lines

    @api.multi
    def validar_report(self):
        return self.write({'state': 'done'})


class TaxBook(models.Model):
    _name="account.move.book.fees.tax"

    def get_monto(self):
        for t in self:
            t.amount = t.debit - t.credit

    tax_id = fields.Many2one('account.tax', string="Impuesto")
    credit = fields.Monetary(string="Créditos", default=0.00)
    debit = fields.Monetary(string="Débitos", default=0.00)
    amount = fields.Monetary(compute="get_monto", string="Monto")
    currency_id = fields.Many2one('res.currency',
        string='Moneda',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility='always')
    book_id = fields.Many2one('account.move.book.fees', string="Libro")
