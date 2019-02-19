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
from openerp import models, api, fields, SUPERUSER_ID, _
from openerp.osv import expression
from utils import to_dsoft_date
from openerp.exceptions import ValidationError
from datetime import datetime
import pytz
import utils
from openerp.tools.float_utils import float_compare


class stock_quant(models.Model, utils.DSoftSystemParamMixin):
    _inherit = "stock.quant"

    @api.model
    def get_purchase_move(self, quant):
        if not quant:
            return None

        history_moves = quant.history_ids
        obj_data = self.env['ir.model.data']
        stock_loc_input = obj_data.xmlid_to_res_id('stock.stock_location_company') #input loc
        stock_loc_supplier = obj_data.xmlid_to_res_id('stock.stock_location_suppliers')

        if history_moves:
            purchase_move = history_moves.filtered(lambda move: move.picking_type_id.code == 'incoming' and move.location_id.id == stock_loc_supplier and move.location_dest_id.id == stock_loc_input)
            return purchase_move
        return None

    @api.model
    def get_invoice(self, quant):
        purchase_move = self.get_purchase_move(quant)
        if purchase_move:
            invoice_line_id = self.env['account.invoice.line'].search([('purchase_line_id', '=', purchase_move.purchase_line_id.id)])
            if invoice_line_id:
                return invoice_line_id[0].invoice_id or None
        return None

    dsoft_cont = fields.Many2one('account.account', string='CONT', copy=True)
    dsoft_denumire = fields.Char(string="DENUMIRE", related='product_id.dsoft_denumire')
    dsoft_available_for_export = fields.Boolean("Poate aparea in bon de consum dsoft", default=False, copy=True)
    dsoft_cod = fields.Char(string="COD", size=12, copy=True)

    cost = fields.Float(string="Cost (PRET_ACHIZ)", copy=True)

    dsoft_nir = fields.Integer(string="NIR", copy=True, default=0)
    dsoft_nr_fact = fields.Char(string="Numar Factura Furnizor", copy=True, default="")

    @api.model
    def _compute_dsoft_cod(self):
        md = self.env['ir.model.data']
        seq = md.get_object_reference('dsoft_accounting', 'sequence_dsoft_cod_prod')[1]
        obj_sequence = self.env['ir.sequence']
        return obj_sequence.next_by_id(seq)


    @api.model
    def _quant_create(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False):
        qty = super(stock_quant, self)._quant_create(qty, move, lot_id=lot_id, owner_id=owner_id,
                                                     src_package_id=src_package_id, dest_package_id=dest_package_id,
                                                     force_location_from=force_location_from,
                                                     force_location_to=force_location_to)

        obj_data = self.env['ir.model.data']
        # stock_loc_stock = obj_data.xmlid_to_res_id('stock.stock_location_stock')
        stock_loc_input = obj_data.xmlid_to_res_id('stock.stock_location_company') #input loc
        stock_loc_supplier = obj_data.xmlid_to_res_id('stock.stock_location_suppliers')

        if move.picking_type_id.code == 'incoming' and move.location_id.id == stock_loc_supplier and move.location_dest_id.id == stock_loc_input:
            qty.dsoft_cod = self._compute_dsoft_cod()

        if 'available_for_dsoft_export' in self._context:
            qty.dsoft_available_for_export = self._context['available_for_dsoft_export']

        return qty

    @api.model
    def quants_get_prefered_domain(self, location, product, qty, domain=None,
                                   prefered_domain_list=[], restrict_lot_id=False, restrict_partner_id=False):
        location_usage_hacked = False
        if location.usage == 'production':
            location.usage = 'internal'
            location_usage_hacked = True
        result = super(stock_quant, self).quants_get_prefered_domain(
            location, product, qty, domain=domain,
            prefered_domain_list=prefered_domain_list, restrict_lot_id=restrict_lot_id,
            restrict_partner_id=restrict_partner_id)
        if location_usage_hacked:
            location.usage = 'production'
        return result

    @api.cr_uid_ids_context
    def _quants_merge(self, cr, uid, solved_quant_ids, solving_quant, context=None):
        super(stock_quant, self)._quants_merge(cr, uid, solved_quant_ids, solving_quant, context=context)
        if len(solved_quant_ids) == 1:
            solved_quant = self.browse(cr, uid, solved_quant_ids, context=context)
            solved_quant.dsoft_available_for_export = solving_quant.dsoft_available_for_export
            solved_quant.dsoft_cod = solving_quant.dsoft_cod
            solved_quant.cost = solving_quant.cost
            solved_quant.dsoft_nir = solving_quant.dsoft_nir
            solved_quant.dsoft_nr_fact = solving_quant.dsoft_nr_fact

    def _quant_split(self, cr, uid, quant, qty, context=None):
        new_quant = super(stock_quant, self)._quant_split(cr, uid, quant, qty, context=None)
        rounding = quant.product_id.uom_id.rounding
        if float_compare(abs(quant.qty), abs(qty), precision_rounding=rounding) <= 0: # if quant <= qty in abs, take it entirely
            return new_quant
        quant.invalidate_cache()

        if new_quant:
            new_quant.dsoft_available_for_export = quant.dsoft_available_for_export
            new_quant.dsoft_cont_cor = quant.dsoft_cont_cor
            new_quant.dsoft_nir = quant.dsoft_nir
            new_quant.dsoft_nr_fact = quant.dsoft_nr_fact
        return new_quant

    @api.model
    def _prepare_journal_item(self, amount, product, qty, analytic_account, account):
        return {'name': product.name,
                'account_id': analytic_account.id,
                'journal_id': self.env.ref('dsoft_accounting.analytic_journal_stock_move').id,
                'user_id': self.env.user.id,
                'product_id': product.id,
                'unit_amount': qty,
                'amount': amount,
                'product_uom_id': product.uom_id.id,
                'general_account_id': account.id,
                'date': fields.Date.today()
        }

    @api.model
    def assign_analytic_account(self, quant, analytic_account_id):
        super(stock_quant, self).assign_analytic_account(quant, analytic_account_id)
        if quant.dsoft_available_for_export and quant.dsoft_cont and analytic_account_id and quant.analytic_account_id:
            analytic_line_from = self._prepare_journal_item(quant.cost * quant.qty, quant.product_id, quant.qty, quant.analytic_account_id, quant.dsoft_cont)
            self.env['account.analytic.line'].create(analytic_line_from)

            analytic_line_to = self._prepare_journal_item(-quant.cost * quant.qty, quant.product_id, quant.qty, analytic_account_id, quant.dsoft_cont)
            self.env['account.analytic.line'].create(analytic_line_to)

    @api.one
    def update_dsoft_values(self, invoice_line_id):
        if invoice_line_id.invoice_id.type == 'in_invoice':
            self.dsoft_cod = invoice_line_id.dsoft_cod
            self.dsoft_cont = invoice_line_id.account_id
            self.cost = invoice_line_id.dsoft_pret_achiz

        self.dsoft_nir = invoice_line_id.dsoft_numar
        self.dsoft_nr_fact = invoice_line_id.dsoft_nr_aviz

        quant_analytic_before = self.analytic_account_id
        if quant_analytic_before != invoice_line_id.account_analytic_id:
            self.env['stock.quant'].assign_analytic_account(self, invoice_line_id.account_analytic_id)


class stock_change_product_qty(models.TransientModel):
    _inherit = "stock.change.product.qty"

    def change_product_qty(self, cr, uid, ids, context=None):
        ctx = context.copy()
        ctx.update(available_for_dsoft_export=False)
        return super(stock_change_product_qty, self).change_product_qty(cr, uid, ids, context=ctx)