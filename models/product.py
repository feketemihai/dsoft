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
from openerp import models, api, fields, _
from datetime import datetime
from utils import DSOFT_DEFAULT_DATE_FORMAT
import logging
from openerp.exceptions import ValidationError
import utils

DSOFT_PRODUCT_ACCOUNTS = [('3021', '3021'), ('371', '371'), ('303', '303'), ('8035', '8035'), ('7588', '7588'), ('7041','7041'), ('7042', '7042'), ('7043', '7043')]
DEFAULT_DSOFT_PRODUCT_ACCOUNT = DSOFT_PRODUCT_ACCOUNTS[0][0]


_logger = logging.getLogger(__name__)


class dsoft_line(models.Model):
    _name = 'dsoft_accounting.dsoft_line'

    dsoft_codg = fields.Char(string=_("CODG")) #only used for import
    dsoft_denumire = fields.Char(string=_("DENUMIRE"), size=30, required=True)
    dsoft_cont = fields.Selection(selection=DSOFT_PRODUCT_ACCOUNTS,
                                  string=_("CONT"), size=7, default=DEFAULT_DSOFT_PRODUCT_ACCOUNT)
    dsoft_um = fields.Char(string=_("UM"))
    dsoft_datauintr = fields.Char(string="DATAUINTR", default="")
    dsoft_cod = fields.Char(string="COD", size=12)
    dsoft_eurocod = fields.Char(string="EUROCOD")
#    dsoft_raft = fields.Char(string="RAFT")
#    dsoft_grupa = fields.Char(string="GRUPA")
#    dsoft_dengrupa = fields.Char(string="DEN_GRUPA")
    dsoft_pret_achiz = fields.Float(string="PRET_ACHIZ")
    dsoft_pret_aman = fields.Float(string="PRET_AMAN")
    dsoft_val_marfa = fields.Float(string="VAL_MARFA")
    dsoft_cantitate = fields.Char(string="CANTITATE")
    dsoft_tva = fields.Float(string="TVA")
    dsoft_val_tva = fields.Float(string="VAL_TVA")


    @api.model
    def create(self, values):
        res = super(dsoft_line, self).create(values)
        try:
            name = " ".join(["(DS)", values.get('dsoft_denumire', '').strip()])
            dsoft_cod = values.get('dsoft_cod', '').strip()
            if dsoft_cod and name:
                categ_id = self.env.ref('dsoft_accounting.dsoft_category')
                if not categ_id.exists():
                    categ_id = self.env['product.category'].create({'name': "dsoft"})

                values.update(categ_id=categ_id.id)
                prod_tmpl = self.env['product.template'].search([('name', '=', name)])
                if not prod_tmpl.exists():
                    um_id = self.env['product.uom'].search([('dsoft_name', '=', values['dsoft_um'])])[0].id
                    values.update({'name': name,
                                   'standard_price': res.dsoft_pret_achiz,
                                   'dsoft_line_id': res.id,
                                   'uom_id': um_id,
                                   'uom_po_id': um_id})
                    prod_tmpl = self.env['product.template'].with_context(dsoft_stock_import=True).create(values)

                prod = self.env['product.product'].search([('product_tmpl_id', '=', prod_tmpl.id)])
                prod.ensure_one()
                prod.update_quant_with_dsoft_values(values.get('dsoft_cantitate', None), values.get("dsoft_codg", None))
                return prod_tmpl
        except:
            _logger.error("error importing line with code: %s" % values.get('dsoft_cod', None), exc_info=True)

        return res


class product_uom(models.Model):
    _inherit = 'product.uom'

    _rec_name = 'dsoft_name'
    _order = 'dsoft_name'
    dsoft_name = fields.Char(string="DSOFT", default="UNDEFINED", translate=True)


class product_template(models.Model, utils.DSoftSystemParamMixin):
    _inherit = "product.template"

    @api.multi
    def _compute_pprod_count(self):
        for prod_tmpl in self:
            prod_tmpl.pprod_count = sum([p.pprod_count for p in prod_tmpl.product_variant_ids])

    dsoft_denumire = fields.Char(string=_("DENUMIRE"), size=30, required=True)
    dsoft_um = fields.Char(string=_("UM"), related="uom_po_id.dsoft_name", readonly=True)
    dsoft_cod = fields.Char(string="COD", size=12)
    dsoft_cont = fields.Many2one('account.account', string='CONT', copy=True, required=True)

    dsoft_line_id = fields.Many2one('dsoft_accounting.dsoft_line', 'DSOFT Import line')

    dsoft_codg = fields.Char(related="dsoft_line_id.dsoft_codg")
    dsoft_datauintr = fields.Char(related="dsoft_line_id.dsoft_datauintr")
    dsoft_pret_achiz = fields.Float(related="dsoft_line_id.dsoft_pret_achiz")
    dsoft_pret_aman = fields.Float(related="dsoft_line_id.dsoft_pret_aman")
    dsoft_val_marfa = fields.Float(related="dsoft_line_id.dsoft_val_marfa")
    dsoft_cantitate = fields.Char(related="dsoft_line_id.dsoft_cantitate")
    dsoft_tva = fields.Float(related="dsoft_line_id.dsoft_tva")
    dsoft_val_tva = fields.Float(related="dsoft_line_id.dsoft_val_tva")

    pprod_count = fields.Integer('Post Porductions Count', compute=_compute_pprod_count)

    @api.model
    def default_get(self, fields):
        res = super(product_template, self).default_get(fields)
        res['cost_method'] = 'real'
        res['valuation'] = 'manual_periodic'
        res['type'] = 'product'
        res['state'] = 'sellable'
        res['purchase_request'] = True
        res['dsoft_cont'] = self.default_cont()
        return res

    def onchange_type(self, cr, uid, ids, type):
        res = super(product_template, self).onchange_type(cr, uid, ids, type)
        if 'value' not in res:
            res['value'] = {}
        res['value']['dsoft_cont'] = self.default_cont_service(cr, uid, context={}) if type == 'service' else self.default_cont(cr, uid, context={})
        return res

    @api.multi
    def action_view_pprods(self):
        products = self._get_products()
        result = self.env.ref('mrp_repair.action_repair_order_tree')
        if len(self.ids) == 1 and len(products) == 1:
            result['context'] = "{'default_product_id': " + str(products[0]) + ", 'search_default_product_id': " + str(products[0]) + "}"
        else:
            result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
            result['context'] = "{}"
        return result.copy_data()[0]


class product_product(models.Model, utils.DSoftSystemParamMixin):
    _inherit = "product.product"

    @api.multi
    def update_quant_with_dsoft_values(self, quantity, analytic_account_id):
        self.ensure_one()
        change_product_qty = self.with_context(
            active_id=self.id,
            active_model='product.product').env['stock.change.product.qty'].create({
                'new_quantity': quantity
            })
        if quantity and float(quantity) > 0:
            quants = self.env['stock.quant'].search([('product_id', '=', self.id),
                                                     ('dsoft_cod', '=', self.dsoft_cod)])
            if not quants.exists():
                change_product_qty.with_context(dsoft_stock_import=True).new_product_qty()

            quant = self.env['stock.quant'].search([('product_id', '=', self.id)],
                                                   limit=1, order='create_date DESC')
            try:
                if self.dsoft_datauintr:
                    quant.in_date = datetime.strptime(self.dsoft_datauintr, DSOFT_DEFAULT_DATE_FORMAT)
            except Exception:
                _logger.error("error importing line with code: %s" % self.dsoft_cod, exc_info=True)

            quant.dsoft_available_for_export = True
            quant.dsoft_cod = self.dsoft_cod
            quant.dsoft_pret_aman = self.dsoft_pret_aman
            quant.cost = self.dsoft_pret_achiz
            quant.dsoft_tva = self.dsoft_tva
            quant.dsoft_val_tva = self.dsoft_val_tva

            if analytic_account_id:
                aa = self.env['account.analytic.account'].search([('code', '=', analytic_account_id)])
                if not aa.exists():
                    aa = self.env['account.analytic.account'].create({'name': "G%s" % analytic_account_id,
                                                                 'type': 'normal',
                                                                 'code': analytic_account_id})
                quant.analytic_account_id = aa[0].id
            _logger.info("imported line with code: %s", quant.dsoft_cod)
        else:
            _logger.error("invalid Quantity %s, line with code: %s" %  (self.dsoft_cantitate, self.dsoft_cod))
