# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import ast

class ColaEnvio(models.Model):
    _name = "sii.cola_envio"

    doc_ids = fields.Char(string="Id Documentos")
    model = fields.Char(string="Model destino")
    user_id = fields.Many2one('res.users')
    tipo_trabajo = fields.Selection(
        [('envio', 'Envío'), ('consulta', 'Consulta')],
        string="Tipo de trabajo")
    active = fields.Boolean(string="Active", default=True)
    att_number = fields.Char(string="Número de atención")

    @api.model
    def _cron_process_queue(self):
        ids = self.search([('active', '=', True)])
        if ids:
            for c in ids:
                docs = self.env[c.model].browse(ast.literal_eval(c.doc_ids))
                if docs[0].sii_send_ident and docs[0].sii_message and \
                        docs[0].sii_result in [
                            'Proceso', 'Rechazado', 'Aceptado']:
                    c.unlink()
                    return
                else:
                    for doc in docs:
                        doc.responsable_envio = c.user_id
                    if c.tipo_trabajo == 'envio':
                        docs.do_dte_send(c.att_number)
                        c.tipo_trabajo = 'consulta'
                    else:
                        docs[0].ask_for_dte_status()
