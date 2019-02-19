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
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import api
from openerp.exceptions import MissingError
import simplejson


DSOFT_DEFAULT_DATE_FORMAT = "%d%m%Y"

def to_dsoft_date(date_field):
    if not date_field:
        return ""
    _date = datetime.strptime(date_field, DEFAULT_SERVER_DATE_FORMAT).date()
    return _date.strftime(DSOFT_DEFAULT_DATE_FORMAT)


class DSoftSystemParamMixin(object):

    @api.model
    def get_dsoft_sys_param(self, xml_id, module='dsoft_accounting'):
        md = self.env['ir.model.data']
        seq = md.get_object_reference(module, xml_id)[1]
        return self.env['ir.config_parameter'].browse(seq).value

    @api.model
    def default_cont(self):
        dsoft_default_cont = self.get_dsoft_sys_param('param_dsoft_accounts_default_cont')
        if dsoft_default_cont:
            default_odoo = self.env['account.account'].search([('code', 'like', dsoft_default_cont + '%')])
            return default_odoo and default_odoo[0].id
        raise MissingError('Eroare cont dsoft default.')

    @api.model
    def default_cont_service(self):
        dsoft_default_cont = self.get_dsoft_sys_param('param_dsoft_accounts_default_cont_service')
        if dsoft_default_cont:
            default_odoo = self.env['account.account'].search([('code', 'like', dsoft_default_cont + '%')])
            return default_odoo and default_odoo[0].id
        raise MissingError('Eroare cont dsoft default.')

    @api.model
    def domain_cont(self):
        accounts = self.get_dsoft_sys_param('param_dsoft_accounts').split(',')
        return [('code', 'in', accounts)]

    @api.model
    def domain_cont_cor(self):
        accounts = self.get_dsoft_sys_param('param_dsoft_accounts_cor').split(',')
        return [('code', 'in', accounts)]
