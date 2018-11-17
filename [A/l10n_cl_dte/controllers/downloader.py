from odoo import models, http, api
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception, content_disposition
import logging
_logger = logging.getLogger(__name__)

class Binary(http.Controller):

    @http.route('/web/binary/download_document', type='http', auth="public")
    @serialize_exception
    def download_document(
            self, model, field, id, filename=None, filetype='xml', **kw):
        """
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        
        Model = request.registry[model]
        _logger.info('Model =========================111: %s' % Model)
        cr, uid, context = request.cr, request.uid, request.context
        fields = [field]
        res = Model.read(cr, uid, [int(id)], fields, context)[0]
        filecontent = res.get(field)
        print(filecontent)
        _logger.info('Model: %s' % Model)
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
