# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Module: quant_work
#    Author: Cojocaru Marcel @Temeron SRL
#    mail:   marcel.cojocaru@gmail.com
#    Copyright (C) 2016- S.C. Beespeed Automatizari S.R.L., Timisoara
#                  http://www.beespeed.ro
#    Contributions:
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


class account_period(models.Model):
    _name = "account.period"
    _inherit = "account.period"

    @api.multi
    def _compute_dsoft_export_file_name(self):
        for period in self:
            period.file_name = 'MIV%s.csv' % datetime.strptime(
                period.date_start, DEFAULT_SERVER_DATE_FORMAT).strftime("%m%y")


    invoice_lines = fields.One2many('dsoft_accounting.invoice_line', 'period_id', string='Linii facturi')
    file_name = fields.Char('Nume fisier csv', compute="_compute_dsoft_export_file_name")

    export_foreign_invoices = fields.Boolean('Exporta facturi externe', default=False)
    export_in_invoices = fields.Boolean('Exporta facturi receptie', default=True)
    export_out_invoices = fields.Boolean('Exporta facturi clienti', default=True)

    @api.model
    def prepare_export_data(self, export, period_id, context):
        invoice_lines = period_id.invoice_lines.filtered(lambda line:  line.invoice_id.state not in ['draft', 'cancel'])

        inv_type = []
        if period_id.export_in_invoices:
            inv_type.append('in_invoice')

        if period_id.export_out_invoices:
            inv_type.append('out_invoice')

        if inv_type:
            invoice_lines = invoice_lines.filtered(
                lambda line: line.invoice_id.type in inv_type)

            if 'export_foreign_invoices' in period_id:
                invoice_lines = invoice_lines.filtered(
                    lambda line: line.invoice_id.dsoft_valuta==False)


            columns_headers, import_data = export._export_data('dsoft_accounting.invoice_line', invoice_lines.ids, context)
            return (columns_headers, import_data)
        return ([], [])
