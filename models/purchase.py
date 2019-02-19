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
from openerp import models, fields


class purchase_order(models.Model):
    _inherit = 'purchase.order'


    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
        list_vals = super(purchase_order, self)._prepare_order_line_move(cr, uid, order, order_line, picking_id, group_id, context=context)

        for val in list_vals:
            val['analytic_account_id'] = order_line.account_analytic_id.id

        return list_vals
