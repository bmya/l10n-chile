from odoo import models, http, api
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception, \
    content_disposition
import logging
_logger = logging.getLogger(__name__)


class Binary(http.Controller):

    @http.route('/web/binary/download_document', type='http', auth="public")
    @serialize_exception
    def download_document(
            self, model, field, id, filename=None, filetype='xml', **kw):
        """
        Download document function
        :param model:
        :param field:
        :param id:
        :param filename:
        :param filetype:
        :param kw:
        :return:
        """
        _logger.info('kwargs: %s' % kw)
        reg_model = request.registry[model]
        _logger.info('reg_model =========================: %s' % model)
        cr, uid, context = request.cr, request.uid, request.context
        fields = [field]
        res = reg_model.read(cr, uid, [int(id)], fields, context)[0]
        filecontent = res.get(field)
        print(filecontent)
        if not filecontent:
            return request.not_found()
        else:
            if not filename:
                filename = '%s_%s' % (model.replace('.', '_'), id)
            headers = [
                ('Content-Type', 'application/%s' % filetype),
                ('Content-Disposition', content_disposition(filename)),
                ('charset', 'utf-8'), ]
            return request.make_response(
                    filecontent, headers=headers, cookies=None)
