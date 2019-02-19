from openerp.addons.web.controllers.main import CSVExport, Export, serialize_exception
from openerp import http
from openerp.http import request
import operator
import simplejson
from datetime import datetime
from openerp.addons.web.controllers.main import content_disposition

class DSoftExport(CSVExport, Export):


    def _export_data(self, model, ids, context):
        proxy = request.env['ir.model.data']
        Model = request.session.model(model)
        exports_id = proxy.get_object_reference('dsoft_accounting', 'dsoft_export_fields')[1]
        export_fields_list = request.env['ir.exports'].sudo().browse(exports_id).export_fields

        fields_data = self.fields_info(
            model, map(operator.itemgetter('name'), export_fields_list))

        fields = [
            {'name': field['name'], 'label': fields_data[field['name']]}
            for field in export_fields_list
        ]

        field_names = map(operator.itemgetter('name'), fields)

        columns_headers = [val['label'].strip() for val in fields]
        data = Model.export_data(ids, field_names, self.raw_data, context=context).get('datas',[])
        return (columns_headers, data)


    @http.route('/dsoft_accounting/export/dsoft', type='http', auth="user")
    @serialize_exception
    def index_dsoft(self, data, token):
        params = simplejson.loads(data)

        Period = request.session.model('account.period')
        context = dict(request.context or {}, **params.get('context', {}))
        period_id = Period.browse(params['ids'])

        columns_headers, import_data = Period.prepare_export_data(self, period_id, context)

        return request.make_response(self.from_data(columns_headers, import_data),
            headers=[('Content-Disposition',
                            content_disposition(period_id.file_name)),
                     ('Content-Type', self.content_type)],
            cookies={'fileToken': token})

    def from_data(self, fields, rows):
        fields = [f.replace("DSOFT Invoice Lines/", "").replace("Linii Bon Consum DSOFT/", "") for f in fields]
        return super(DSoftExport, self).from_data(fields, rows)
