# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, time
import logging

indicadores = {
    'SBIFUSD': ['dolar', 'Dolares', 'sbif_usd', 'USD'],
    'SBIFEUR': ['euro', 'Euros', 'sbif_eur', 'EUR'],
    'SBIFUF': ['uf', 'UFs', 'sbif_uf', 'UF'],
    'SBIFUTM': ['utm', 'UTMs', 'sbif_utm', 'UTM']}

_logger = logging.getLogger(__name__)


class L10nClFinancialIndicators(models.Model):
    _inherit = "webservices.server"

    @api.multi
    def action_update_currency(self):
        self.ensure_one()
        _logger.info('name: {}'.format(self.name))
        _logger.info('url: {}'.format(self.url))
        a = self.generic_connection()
        _logger.info('Data received... status: {}'.format(a['status']))
        if a['status'] != 200:
            _logger.warning(
                'could not establish connection: {}'.format(a['data']))
            return

        data_json = a['data']
        
        _logger.info(
            'Data showed locally... Date: {}, Value: {}'.format(
            data_json[indicadores[self.name][1]][0]['Fecha'],
            data_json[indicadores[self.name][1]][0]['Valor']))
        
        rate = float(
            data_json[indicadores[self.name][1]][0]['Valor'].replace(
                '.', '').replace(',', '.'))

        _logger.info('rate: {}'.format(rate))

        rate_name = fields.Datetime.to_string(datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0))

        currency_id = self.env['res.currency'].search([(
                    'name', '=', indicadores[self.name][3])])

        if not currency_id:
            _logger.warning(
                'No esta cargada "%s" como moneda. No se actualiza.'
                % indicadores[self.name][1])
        else:
            _logger.info(
                'Actualizando la moneda "{}"'.format(indicadores[self.name][1]))
            values = {
                'currency_id': currency_id.id,
                'rate': 1/rate,
                'name': rate_name}
            rates = self.env['res.currency.rate'].create(values)
            print "se actualizó la moneda"
            print indicadores[self.name][1]

    @api.model
    def currency_schedule_update(self):
        for indic in indicadores.iteritems():
            _logger.info(
                'Iterando la moneda "{}" por proceso planificado'.format(
                    indic[0]))
            webservice_rec = self.env['webservices.server'].search(
                [('name', '=', indic[0])])
            if webservice_rec:
                webservice_rec.action_update_currency()
        return True
