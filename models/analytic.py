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

class InventoryUnit(models.Model):
    _name = 'dsoft_accounting.inventory_unit'

    _order = 'code'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)

    @api.multi
    def name_get(self):
        res = []
        for invu in self:
            res.append((invu.id, invu.name + " (" + invu.code + ")"))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
         objs = self.search(['|', ('name', 'ilike', name), ('code', 'ilike', name)], limit=limit)
         return objs.name_get()


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    inventory_unit = fields.Many2one(comodel_name='dsoft_accounting.inventory_unit', string='Inventory Unit')

    @api.multi
    def name_get(self):
        res = []
        for aaa in self:
            name = self._get_one_full_name(aaa)
            if aaa.inventory_unit:
                name += " (" + aaa.code + ")"
            res.append((aaa.id, name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        result = super(AccountAnalyticAccount, self).name_search(
            name=name, args=args, operator=operator, limit=limit)
        analytics = self.search([('code', 'like', name)])
        result2 = analytics.name_get()
        return list(set(result2 + result))