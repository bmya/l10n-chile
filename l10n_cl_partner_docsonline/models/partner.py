# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import Warning as UserError
import json
import logging
import requests

_logger = logging.getLogger(__name__)
tax_resp_category = {u'1': u'res_IVARI',  u'2': u'res_BH'}
controlled_fields = ['name', 'street', 'email']

class PartnerDataSII(models.Model):
    _inherit = 'res.partner'

    def press_to_update(self):
        try:
            if int(self.document_number.replace('-', '').replace(
                    'K', '').replace('k', '').replace('.', '')) == 0:
                raise UserError(
                    u'Debe existir el RUT para utilizar la actualización \
desde www.documentosonline.cl')
            self._get_data_from_docsonline()
        except AttributeError:
            raise UserError(
                u'Debe existir el RUT para utilizar la actualización desde \
www.documentosonline.cl')

    def _get_docsonline_data(self):
        conf = self.env['ir.config_parameter']
        docsonline_data = {
            'url': conf.get_param('docsonline.url'),
            'token': conf.get_param('docsonline.token'), }
        for f in controlled_fields:
            docsonline_data['replace_%s' % f] = conf.get_param(
                'docsonline.replace_%s' % f) in [
                'True', 'true', '1', 'Verdadero', 'verdadero']
        return docsonline_data

    def _get_partner_turn_id(self, giro_id):
        act_obj = self.env['partner.activities']
        act_record = act_obj.search(
            [('code', '=', giro_id)])
        _logger.info('actividad(es): {}'.format(act_record))
        return act_record

    def _get_partner_location_id(self, comuna_id):
        try:
            return self.env.ref(
                'l10n_cl_counties.CL{}'.format(comuna_id))
        except:
            return False

    @api.multi
    @api.onchange('document_number')
    def _get_data_from_docsonline(self):
        self.ensure_one()
        if self.document_type_id != self.env.ref('l10n_cl_invoice.dt_RUT'):
            return
        if not self.document_number:
            return
        self.document_type_id = self.env.ref('l10n_cl_invoice.dt_RUT')
        rut = str(
            int(self.document_number.replace('.', '').replace('-', '')[:-1]))
        docsonline_data = self._get_docsonline_data()
        host = docsonline_data['url']
        headers = {}
        headers['Authorization'] = 'Basic %s' % docsonline_data['token']
        headers['Accept-Encoding'] = 'gzip, deflate, identity'
        headers['Accept'] = '*/*'
        headers['User-Agent'] = 'python-requests/2.6.0 CPython/2.7.6 \
#Linux/3.13.0-88-generic'
        headers['Connection'] = 'keep-alive'
        headers['Content-Type'] = 'application/json'
        headers['charset'] = 'utf-8'
        _logger.info('estoy consultando con este header %s' % headers)
        data = {
            'params': {
                'vat': rut
            }
        }
        _logger.info('estoy consultando con este data %s' % json.dumps(data))
        r = requests.post(
            host + '/partner/jget',
            headers=headers,
            data=json.dumps(data))
        if r.status_code != 200:
            _logger.info('Error al obtener datos del contribuyente:')
            return {'error': 'Error al obtener datos del contribuyente'}
        else:
            partner_values = json.loads(r.text)['result']
            _logger.info('Conexion correcta: %s' % partner_values)
            try:
                if partner_values['error']:
                    _logger.warning('DocsOnline: Unauthorized')
                    raise UserError(
                        'No pudo obtener datos de www.documentosonline.cl: %s'
                        % partner_values['error'])
            except KeyError:
                pass
            _logger.info('se muestra el contenido de docsonline_data:')
            _logger.info(docsonline_data)
            for k, v in partner_values.iteritems():
                if k in ['partner_activities_ids', 'location_id']:
                    continue
                try:
                    if k in controlled_fields:
                        _logger.info('Estoy en campo controlado: %s' % k)
                        if getattr(self, k):
                            _logger.info('El campo %s tiene contenido' % k)
                            _logger.info(docsonline_data['replace_%s' % k])
                            if docsonline_data['replace_%s' % k]:
                                _logger.info('%s se reemplaza con %s' % (k, v))
                                pass
                            else:
                                _logger.info('%s no se reemplaza' % k)
                                continue
                    setattr(self, k, v)
                    _logger.info('Se ejecuta el reemplazo de %s' % k)
                except:
                    _logger.info('Excepcion general')
                    continue
            try:
                location_id = self._get_partner_location_id(
                    partner_values['location_id'])
                _logger.info('location id: {}'.format(location_id))
                self.country_id = location_id.country_id
                self.city_id = location_id.id
                self.city = location_id.name
            except KeyError:
                _logger.warning(
                    'could not get location id info from DocsOnline')

            try:
                giro = self._get_partner_turn_id(
                    str(partner_values['partner_activities_ids']['code']))
                _logger.info('giro: {}'.format(giro.id))
                self.partner_activities_ids = [(4, giro.id)]
                _logger.info('Tax category: {}'.format(giro.tax_category))

                if True:
                    self.responsability_id = self.env.ref(
                        'l10n_cl_invoice.{}'.format(
                            tax_resp_category[giro.tax_category]))
                else:
                    _logger.warning(
                        'tax category could not be properly selected')
            except:
                _logger.warning('could not activity from DocsOnline')
