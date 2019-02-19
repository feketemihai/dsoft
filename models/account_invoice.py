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
from openerp import models, fields, api, _
import pytz
import logging
from datetime import datetime
from openerp.exceptions import MissingError, Warning
import openerp.addons.decimal_precision as dp
from utils import to_dsoft_date
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta
import utils

_logger = logging.getLogger(__name__)


class res_partner_mail(models.Model):
    _inherit = "res.partner"

    _defaults = {
        'notify_email': lambda *args: 'none'
    }


class account_invoice(models.Model, utils.DSoftSystemParamMixin):
    _inherit = "account.invoice"

    _order = "date_invoice desc"

    _track = {
        'type': {
        },
        'state': {
            'account.mt_invoice_paid': lambda self, cr, uid, obj, ctx=None: obj.state == 'paid' and obj.type in ('out_invoice', 'out_refund')
        }
    }

    @api.model
    def create(self, vals):
        res = super(account_invoice, self).create(vals)
        res.dsoft_numar = 0
        return res

    @api.multi
    def _compute_dsoft_tip_doc(self):
        for inv in self:
            inv.dsoft_tip_doc = '1' if inv.type == 'in_invoice' or inv.type == 'in_refund' else '5'

    @api.multi
    def _compute_dsoft_fel_misc(self):
        for inv in self:
            inv.dsoft_fel_misc = '1' if inv.type == 'in_invoice' or inv.type == 'in_refund' else '2'

    @api.multi
    def _compute_dsoft_datascad(self):
        for inv in self:
            inv.dsoft_datascad = to_dsoft_date(inv.date_due)

    @api.multi
    @api.depends('date_invoice')
    def _compute_dsoft_data_aviz(self):
        for inv in self:
            inv.dsoft_data_aviz = to_dsoft_date(inv.date_invoice)

    @api.multi
    def _compute_dsoft_cont_cor(self):
        for inv in self:
            inv.dsoft_cont_cor = inv.account_id and inv.account_id.code.rstrip("0") or ''

    @api.multi
    def create_dsoft_invoice_lines(self):
        self.env['dsoft_accounting.invoice_line'].search([('invoice_id', '=', self.id)]).unlink()
        for line in self.invoice_line:
            if line.name != 'TOTAL-F' and line.product_id.type != 'service':
                self.env['account.invoice.line'].create_dsoft_lines(line)
            else:
                self.env['account.invoice.line']._create_dsoft_line_from_quant(line, None)

    @api.multi
    def _compute_dsoft_numar(self):
        for inv in self:
            sequence = inv.journal_id.sequence_id
            if inv.type == 'in_invoice':
                if not inv.internal_number and not inv.dsoft_numar:
                    t = datetime.now(pytz.timezone(self._context.get('tz') or 'UTC'))
                    year = int(t.strftime('%Y'))
                    inv.dsoft_numar = int(str(year) + str(sequence.number_next -1))
            elif inv.type in ('out_invoice', 'out_refund'):
                if not inv.internal_number and not inv.dsoft_numar:
                    inv.dsoft_numar = sequence.number_next - 1
                else:
                    int_nb = inv.internal_number and inv.internal_number.split('-') or None
                    inv.dsoft_numar = int(int_nb and len(int_nb) > 1 and int_nb[1] or "0")

            inv.dsoft_data = to_dsoft_date(inv.date_invoice)

    @api.multi
    def action_number(self):
        self.ensure_one()
        if not self.dsoft_codfur:
            raise Warning("Cod furnizor/client nu este completat.")

        if self.currency_id.name != 'RON':
            raise Warning("Nu se poate valida o factura decat in RON.")

        self._compute_dsoft_numar()
        self.create_dsoft_invoice_lines()

        result = super(account_invoice, self).action_number()

        for line in self.dsoft_invoice_line:
            line.update_quants_dsoft_values()

        return result


    @api.one
    def _compute_amount_total_dsoft(self):
        amount_untaxed = sum(line.dsoft_valoare for line in self.dsoft_invoice_line)
        amount_tax = sum(line.dsoft_val_tva for line in self.dsoft_invoice_line)
        self.dsoft_amount_total = amount_untaxed + amount_tax

    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount')
    def _compute_amount(self):
        sign = self.type in ('in_refund', 'out_refund') and -1 or 1
        self.amount_untaxed = sign * sum(line.price_subtotal for line in self.invoice_line)
        self.amount_tax = sign * sum(line.amount for line in self.tax_line)
        self.amount_total = self.amount_untaxed + self.amount_tax

    @api.multi
    @api.depends('supplier_invoice_number')
    def _compute_dsoft_nr_aviz(self):
        for inv in self:
            if inv.type == 'in_invoice':
                inv.dsoft_nr_aviz = inv.supplier_invoice_number
            elif inv.type in ('out_invoice', 'out_refund'):
                int_nb = inv.internal_number and inv.internal_number.split('-') or None
                inv.dsoft_nr_aviz = int(int_nb and len(int_nb) > 1 and int_nb[1] or "0")

    def _compute_domain_cont_cor(self):
        return self.domain_cont_cor()

    account_id = fields.Many2one('account.account', string='Account',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        help="The partner account used for this invoice.", domain=_compute_domain_cont_cor)

    dsoft_invoice_line = fields.One2many('dsoft_accounting.invoice_line', 'invoice_id', string='Invoice Lines',
                                   readonly=True, copy=False)

    dsoft_codfur = fields.Char(string="CODFUR", related="partner_id.dsoft_codfur")

    dsoft_cont_cor = fields.Char(string='CONT_COR', size=7, compute="_compute_dsoft_cont_cor")
    dsoft_tip_doc = fields.Char(string="TIP_DOC", readonly=True, size=1, compute='_compute_dsoft_tip_doc')
    dsoft_fel_misc = fields.Char(string="FEL_MISC", readonly=True, size=1, compute='_compute_dsoft_fel_misc')
    dsoft_numar = fields.Integer(string="NUMAR", default=False)
    dsoft_data = fields.Char(string="DATA")
    dsoft_anulat = fields.Selection([('A', 'A')], string="ANULAT")
    dsoft_comanda = fields.Char(string="COMANDA", size=25)
    dsoft_nr_aviz = fields.Char(string="NR_AVIZ", size=10, compute="_compute_dsoft_nr_aviz")
    dsoft_datascad = fields.Char(string="DATASCAD", compute="_compute_dsoft_datascad")
    dsoft_data_aviz = fields.Char(string="DATA_AVIZ", compute="_compute_dsoft_data_aviz")

    dsoft_jurnal = fields.Selection([
        (' ', 'Spatiu'),
        ('TI', 'TI'),
        ('EU', 'EU'),
        ('NE', 'NE'),
        ('15', '15'),
        ('AS', 'AS'),
        ('AF', 'AF'),
        ('ES', 'ES')], required=True, default=' ', string="JURNAL")

    dsoft_agent = fields.Char(string="AGENT", size=6)
    dsoft_tip_cec = fields.Char(string="TIP_CEC", size=2)
    dsoft_numar_cec = fields.Integer(string="NUMAR_CEC", default=False)
    #dsoft_tva_incas = fields.Selection([('DA', 'DA')], string="TVA_INCAS")
    dsoft_tva_incas = fields.Selection(related="partner_id.dsoft_tva_incas")

    dsoft_altec = fields.Float(string="ALTEC", help=_("Alte Cheltuieli (valuta)"), digits=(12, 2), default=None)

    dsoft_amount_total = fields.Float(string='Total DSOFT (VALOARE + VAL_TVA)', digits=dp.get_precision('Account'),
                                      readonly=True, compute='_compute_amount_total_dsoft')

    amount_untaxed = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')

    global_discount = fields.Float(string='DISCOUNT', digits=dp.get_precision('Account'))

    @api.multi
    def onchange_payment_term_date_invoice(self, payment_term_id, date_invoice):
        res = super(account_invoice, self).onchange_payment_term_date_invoice(payment_term_id, date_invoice)
        res['value'].update(period_id=self.env['account.period'].find(fields.Date.from_string(date_invoice))[:1].id)
        return res

    @api.multi
    def distribute_discount(self):
        for inv in self:
            for line in inv.invoice_line:
                line.discount = inv.global_discount

    @api.multi
    def purchase_open(self):
        self.ensure_one()

        id = None
        try:
            id = self.invoice_line[0].purchase_line_id.order_id.id
        except:
            pass
        return {
            'type': 'ir.actions.act_window',
            'name': 'Achizitii',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'views': [[self.env.ref('purchase.purchase_order_tree').id, "tree"],
                      [False, "form"]],
            'domain': [('id', '=', id)]
        }


class account_invoice_line(models.Model, utils.DSoftSystemParamMixin):
    _inherit = "account.invoice.line"

    @api.multi
    @api.depends('invoice_line_tax_id', 'price_unit')
    def _get_compute_tax_subtotal(self):
        for line in self:
            if line.name == 'TOTAL-F':
                line.tax_subtotal = line.tax_subtotal_internal
                continue
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_id.compute_all(price, line.quantity,
                                                         product=line.product_id,
                                                         partner=line.invoice_id.partner_id)
            taxes = taxes['taxes']
            if line.invoice_id and taxes:
                val_taxes = taxes[0]['amount']
                line.tax_subtotal =  line.invoice_id.currency_id.round(val_taxes)

    @api.multi
    def _set_tax_subtotal(self):
        for line in self:
            line.tax_subtotal_internal = line.tax_subtotal

    @api.model
    def dsoft_analytic_account_code(self, line):
        return line.account_analytic_id.inventory_unit.code

    @api.multi
    @api.depends('account_analytic_id')
    def _compute_dsoft_gestiune(self):
        for line in self:
            line.dsoft_gestiune = self.dsoft_analytic_account_code(line)


    @api.multi
    @api.depends('price_unit', 'discount')
    @api.onchange('price_unit', 'discount')
    def _compute_dsoft_pret_achiz(self):
        for line in self:
            if line.name == 'TOTAL-F':
                line.dsoft_pret_achiz = 0
                continue
            if line.invoice_id.type == 'in_invoice':
                line.dsoft_pret_achiz = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

    @api.multi
    def _compute_dsoft_pret_liv(self):
        for line in self:
            if line.invoice_id.type in ('out_invoice', 'out_refund'):
                sign = line.invoice_id.type in ('in_refund', 'out_refund') and -1 or 1
                line.dsoft_pret_liv = sign * line.price_unit * (1 - (line.discount or 0.0) / 100.0)

    @api.multi
    def _compute_dsoft_pret_aman(self):
        for line in self:
            if line.name == 'TOTAL-F':
                line.dsoft_pret_aman = 0
                continue
                # do not use line.dsoft_pret_achiz instead of price because is rounded at 2 decimals, the end result won't be the same
            sign = line.invoice_id.type in ('in_refund', 'out_refund') and -1 or 1
            price = sign * line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.invoice_line_tax_id.compute_all(price, 1, product=line.product_id, partner=line.invoice_id.partner_id)
            dsoft_pret_aman = taxes['total_included']
            if line.invoice_id:
                line.dsoft_pret_aman = dsoft_pret_aman

    @api.multi
    def _compute_dsoft_valoare(self):
        self._compute_dsoft_pret_achiz()
        for line in self:
            if line.name == 'TOTAL-F':
                line.dsoft_valoare = line.price_unit
                continue
            price = line.dsoft_pret_achiz if line.invoice_id.type == 'in_invoice' else line.dsoft_pret_liv
            taxes = line.invoice_line_tax_id.compute_all(price, line.dsoft_cantitate,
                                                         product=line.product_id,
                                                         partner=line.invoice_id.partner_id)
            dsoft_valoare = taxes['total']
            if line.invoice_id:
                sign = line.invoice_id.type in ('in_refund', 'out_refund') and -1 or 1
                line.dsoft_valoare = line.invoice_id.currency_id.round(sign * dsoft_valoare)

    @api.multi
    def _compute_dsoft_tva(self):
        for line in self:
            line.dsoft_tva = sum([int(tax.amount * 100) for tax in line.invoice_line_tax_id if 'TOTAL-F-TAX' not in tax.description])

    @api.multi
    def _compute_dsoft_cantitate(self):
        for line in self:
            line.dsoft_cantitate = line.quantity

    @api.model
    def _default_account(self):
        return self.default_cont()

    @api.model
    def _default_account_product(self, product):
        return product.dsoft_cont and product.dsoft_cont.id or self._default_account()

    def _compute_domain_cont(self):
        return self.domain_cont()

    @api.multi
    def _compute_dsoft_comanda(self):
        for line in self:
            if self._context.get('type') in ('out_invoice', 'out_refund') or line.invoice_id.type in ('out_invoice', 'out_refund'):
                line.dsoft_comanda = "//" + line.account_analytic_id.code if line.account_analytic_id else ""
            else:
                line.dsoft_comanda = line.invoice_id.dsoft_comanda

    account_id = fields.Many2one('account.account', string='CONT',
        required=True, domain=_compute_domain_cont,
        default=_default_account, help="The income or expense account related to the selected product.")

    tax_subtotal = fields.Float(string=_("Tax subtotal"), compute='_get_compute_tax_subtotal',
                                inverse='_set_tax_subtotal', store=True, readonly=True)

    tax_subtotal_internal = fields.Float(string=_("Tax subtotal"), default=0.0)

    type = fields.Selection(related="invoice_id.type")
    partner_id = fields.Many2one('res.partner', related="invoice_id.partner_id")
    fiscal_position = fields.Many2one('account.fiscal.position', related='invoice_id.fiscal_position')
    currency_id = fields.Many2one('res.currency', related="invoice_id.currency_id")
    company_id = fields.Many2one('res.company', related="invoice_id.company_id")
    journal_id = fields.Many2one('account.journal', related="invoice_id.journal_id")

    dsoft_cont_cor = fields.Char(string='CONT_COR', related="invoice_id.dsoft_cont_cor")
    dsoft_tip_doc = fields.Char(string="TIP_DOC", related="invoice_id.dsoft_tip_doc")
    dsoft_fel_misc = fields.Char(string="FEL_MISC", related="invoice_id.dsoft_fel_misc")
    dsoft_numar = fields.Integer(string="NUMAR", related="invoice_id.dsoft_numar")
    dsoft_data = fields.Char(string="DATA", related="invoice_id.dsoft_data")
    dsoft_anulat = fields.Selection(string="ANULAT", related="invoice_id.dsoft_anulat")
    dsoft_comanda = fields.Char(string="COMANDA", compute="_compute_dsoft_comanda")
    dsoft_nr_aviz = fields.Char(string="NR_AVIZ", related="invoice_id.dsoft_nr_aviz")
    dsoft_datascad = fields.Char(string="DATASCAD", related="invoice_id.dsoft_datascad")
    dsoft_data_aviz = fields.Char(string="DATA_AVIZ", related="invoice_id.dsoft_data_aviz")

    dsoft_jurnal = fields.Selection(string="JURNAL", related="invoice_id.dsoft_jurnal")
    dsoft_agent = fields.Char(string="AGENT", related="invoice_id.dsoft_agent")
    dsoft_tip_cec = fields.Char(string="TIP_CEC", related="invoice_id.dsoft_tip_cec")
    dsoft_numar_cec = fields.Integer(string="NUMAR_CEC", related="invoice_id.dsoft_numar_cec")
    dsoft_tva_incas = fields.Selection(string="TVA_INCAS", related="invoice_id.dsoft_tva_incas")

    dsoft_gestiune = fields.Char(string=_("GESTIUNE"), compute="_compute_dsoft_gestiune", help="Codul gestiunii")
    dsoft_codfur = fields.Char(string="CODFUR", related='invoice_id.dsoft_codfur')
    dsoft_denfur = fields.Char(string="DENFUR", related='partner_id.dsoft_denfur')


    dsoft_denumire = fields.Char(string=_("DENUMIRE"), related='product_id.dsoft_denumire')
    dsoft_um = fields.Char(string=_("UM"), related='product_id.dsoft_um')

    dsoft_pret_valut = fields.Float(string=_("PRET_VALUT"), digits=(15, 7), default=False)
    dsoft_tip_valut = fields.Char(string=_("TIP_VALUT"), size=3)
    dsoft_curs_valut = fields.Float(string=_("CURS_VALUT"), digits=(8, 4), default=False)
    dsoft_curs_fact = fields.Float(string=_("CURS_FACT"), digits=(8, 4), default=False)
    dsoft_val_valut = fields.Float(string=_("VAL_VALUT"), digits=(14, 2), default=False)

    dsoft_cod = fields.Char(string=_("COD"))
    dsoft_cantitate = fields.Float(string=_("CANTITATE"), digits=(11, 3), compute="_compute_dsoft_cantitate")

    dsoft_pret_achiz = fields.Float(string=_("PRET_ACHIZ"), digits=(14, 2), compute='_compute_dsoft_pret_achiz', default=False)
    dsoft_pret_liv = fields.Float(string=_("PRET_LIV"), digits=(14, 2), compute='_compute_dsoft_pret_liv', default=False)
    dsoft_pret_aman = fields.Float(string=_("PRET_AMAN"), digits=(14, 2), compute='_compute_dsoft_pret_aman', default=False)
    dsoft_valoare = fields.Float(string=_("VALOARE"),  digits=(14, 2), compute='_compute_dsoft_valoare')
    dsoft_tva = fields.Integer(string=_("TVA"), compute='_compute_dsoft_tva', default=False)
    dsoft_altec = fields.Float(sting="ALTEC", related='invoice_id.dsoft_altec', help=_("Alte Cheltuieli (valuta)"))

    @api.model
    def create(self, values):
        if values.get('product_id', None):
            product = self.env['product.product'].browse(values['product_id'])
            values['account_id'] = self._default_account_product(product)
        return super(account_invoice_line, self).create(values)

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):

        if not partner_id and 'partner_id' in self._context:
            partner_id = self._context['partner_id']
        result = super(account_invoice_line, self).product_id_change(
            product, uom_id, qty=qty, name=name, type=type, partner_id=partner_id,
            fposition_id=fposition_id, price_unit=price_unit, currency_id=currency_id,
            company_id=company_id)
        product = self.env['product.product'].browse(product)
        result['value']['account_id'] = self._default_account_product(product)
        return result

    @api.model
    def default_get(self, fields):
        res = super(account_invoice_line, self).default_get(fields)
        return res

    @api.multi
    def action_open_invoice_line(self):
        self.ensure_one()

        if self.invoice_id.type == 'in_invoice':
            form = self.env.ref('dsoft_accounting.dsoft_invoice_line_supplier_form')
            ctx = self._context.copy()
            ctx.update(active_model='account.invoice.line', active_id=self.id, active_ids=self.ids)
            value = {
                'type': 'ir.actions.act_window',
                'name': 'Linie Factura',
                'view_type': 'form',
                #            'flags': {'action_buttons': True},
                'view_mode': 'form',
                'res_id': self.id,
                'res_model': 'account.invoice.line',
                'view_id': form.id,
                'target': 'new',
                'context': ctx
            }
            return value
        return None

    @api.multi
    def do_save(self):
        return True

    @api.model
    def _prepare_dsoft_line_values(self, line, quant):
        values = line.copy_data()[0]
        values['invoice_line_id'] = line.id
        values['quant_id'] = quant and quant[0].id or None
        if line.invoice_id.type == 'in_invoice':
            values['quantity'] = line.quantity
            values['dsoft_cod'] = values['dsoft_cod'] or (quant and quant[0].dsoft_cod or '')
        elif line.invoice_id.type in ('out_invoice', 'out_refund'):
            values['quantity'] = quant and quant.qty or line.quantity
            values['dsoft_cod'] = quant and quant[0].dsoft_cod or ''
        return values

    @api.model
    def _create_dsoft_line_from_quant(self, line, quant):
        if quant and not quant[0].dsoft_available_for_export:
            return
        values = self._prepare_dsoft_line_values(line, quant)
        self.env['dsoft_accounting.invoice_line'].create(values)

    @api.model
    def _get_quants(self, line):
        obj_data = self.env['ir.model.data']
        quants = []
        move_obj = self.env['stock.move']
        if line.invoice_id.type == 'in_invoice':
            stock_loc_input = obj_data.xmlid_to_res_id('stock.stock_location_company') #input location
            move = move_obj.search([('product_id', '=', line.product_id.id),
                                    ('purchase_line_id', '=', line.purchase_line_id.id),
                                    ('location_dest_id', '=', stock_loc_input),
                                    ('state', '=', 'done')], limit=1)
        elif line.invoice_id.type in ('out_invoice', 'out_refund'):
            so = self.env['sale.order'].search([('invoice_ids', 'in', [line.invoice_id.id])])
            loc_stock = self.env.ref('stock.stock_location_stock')
            loc_output = self.env.ref('stock.stock_location_output')
            move = self.env['stock.move'].search([('product_id', '=', line.product_id.id),
                                                  ('location_id', '=', loc_stock.id),
                                                  ('location_dest_id', '=', loc_output.id),
                                                  ('picking_id', 'in', so.picking_ids.ids)], limit=1)

        if move:
            quants = move.quant_ids | move.reserved_quant_ids
            if quants:
                dsoft_cod = quants[0].dsoft_cod
                if line.invoice_id.type == 'in_invoice':
                    #if there are more than one quants (initial quant splitted),
                    # then they have to have the same dsoft_cod, there is no other possibility
                    quant_with_different_codes = filter(lambda x: x.dsoft_cod != dsoft_cod, quants)
                    if len(quant_with_different_codes) > 0:
                        raise MissingError("Eroare la identificarea cantitatilor.")

                elif line.invoice_id.type in ('out_invoice', 'out_refund'):
                    quant_with_no_dsoft_pret_achiz = filter(lambda x: x.cost == 0, quants)
                    if len(quant_with_no_dsoft_pret_achiz) > 0:
                        raise MissingError("Eroare la identificarea cantitatilor. Una din cantitati are pretul de achizitie 0.")
                    sum_quants = sum([qnt.qty for qnt in quants])
                    if sum_quants < line.quantity:
                        raise MissingError("Eroare la identificarea cantitatilor. Cantitati insuficiente in magazie.")
            else:
                if line.invoice_id.type == 'out_invoice':
                    raise MissingError("Produsul -- %s -- nu s-a transferat la iesire" % line.product_id.name)

        elif line.product_id.name not in ['TOTAL-F', 'DSOFT_TRANSPORT1', 'DSOFT_TRANSPORT2']:
            if line.invoice_id.type == 'in_invoice':
                raise MissingError("Produsul -- %s -- nu s-a transferat la intrare" % line.product_id.name)
            elif line.invoice_id.type == 'out_invoice':
                raise MissingError("Produsul -- %s -- nu s-a transferat la iesire" % line.product_id.name)

        return quants

    @api.model
    def create_dsoft_lines(self, line):
        quants = self._get_quants(line)

        for qnt in quants:
            qnt.dsoft_available_for_export = True

        if line.invoice_id.type == 'in_invoice':
            self._create_dsoft_line_from_quant(line, quants and quants[0] or None)
        elif line.invoice_id.type in ('out_invoice', 'out_refund'):
            first_qnt = quants[0]
            same_quants = all([qnt.dsoft_cod == first_qnt.dsoft_cod for qnt in quants])
            if same_quants:
                self._create_dsoft_line_from_quant(line, quants)
            else:
                for quant in quants:
                    self._create_dsoft_line_from_quant(line, quant)

        return None


class dsoft_account_invoice_line(models.Model):
    _name = "dsoft_accounting.invoice_line"
    _inherits = {"account.invoice.line":'invoice_line_id'}

    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice Line', required=True, ondelete="cascade")
    quant_id = fields.Many2one('stock.quant', 'Quant')
    quantity = fields.Float(string='Quantity', digits= dp.get_precision('Product Unit of Measure'),
                            required=True, default=1)

    dsoft_cont = fields.Char(string=_("CONT"), size=7, compute="_compute_dsoft_cont")
    dsoft_pret_achiz = fields.Float(string=_("PRET_ACHIZ"), digits=(14, 2), compute='_compute_dsoft_pret_achiz1', default=0.0)
    dsoft_cantitate = fields.Float(string=_("CANTITATE"), digits=(11, 3), compute="_compute_dsoft_cantitate1")
    dsoft_cod = fields.Char(string=_("COD"), compute="_compute_dsoft_cod")
    dsoft_valoare = fields.Float(string=_("VALOARE"),  digits=(14, 2), compute='_compute_dsoft_valoare1')
    dsoft_val_tva = fields.Float(string=_("VAL_TVA"),  digits=(12, 2), compute='_compute_dsoft_val_tva', default=0.0)
    dsoft_pret_aman = fields.Float(string=_("PRET_AMAN"), digits=(14, 2), compute='_compute_dsoft_pret_aman1',
                                   default=False)
    period_id = fields.Many2one('account.period', compute="_compute_period_id", store=True)

    @api.multi
    @api.depends('quant_id')
    def _compute_dsoft_cont(self):
        for line in self:
            if line.product_id.type == 'service' or line.product_id.name == 'TOTAL-F':
                line.dsoft_cont = line.account_id and line.account_id.code.rstrip("0")
            else:
                line.dsoft_cont = line.quant_id and line.quant_id.dsoft_cont and line.quant_id.dsoft_cont.code.rstrip('0') or ''

    @api.multi
    @api.depends('invoice_id.period_id')
    def _compute_period_id(self):
        for line in self:
            line.period_id = line.invoice_id.period_id

    @api.multi
    def _compute_dsoft_val_tva(self):
        for line in self:
            if line.name == 'TOTAL-F':
                line.dsoft_val_tva = line.tax_subtotal
                continue

            sign = line.invoice_id.type in ('in_refund', 'out_refund') and -1 or 1
            price = sign * line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_id.compute_all(price, line.dsoft_cantitate,
                                                         product=line.product_id,
                                                         partner=line.invoice_id.partner_id)
            taxes = taxes['taxes']
            if line.invoice_id and taxes:
                val_taxes = taxes[0]['amount']
                line.dsoft_val_tva = line.invoice_id.currency_id.round(val_taxes)
            else:
                line.dsoft_val_tva = 0.0

    @api.multi
    def _compute_dsoft_valoare1(self):
        for line in self:
            if line.name == 'TOTAL-F':
                line.dsoft_valoare = line.price_unit
            else:
                if line.invoice_id.type == 'in_invoice':
                    line.dsoft_valoare = line.dsoft_cantitate * line.dsoft_pret_achiz
                else:
                    line.dsoft_valoare = line.dsoft_cantitate * line.dsoft_pret_liv

    @api.multi
    def _compute_dsoft_cantitate1(self):
        for line in self:
            if line.invoice_id.type in ('out_invoice', 'out_refund'):
                line.dsoft_cantitate = line.quant_id and line.quant_id.qty or line.invoice_line_id.dsoft_cantitate
            else:
                line.dsoft_cantitate = line.invoice_line_id.dsoft_cantitate

    @api.multi
    def _compute_dsoft_cod(self):
        for line in self:
            line.dsoft_cod = line.quant_id and line.quant_id.dsoft_cod or line.invoice_line_id.dsoft_cod

    @api.multi
    def _compute_dsoft_pret_aman1(self):
        for line in self:
            if line.quant_id:
                sign = line.invoice_id.type in ('in_refund', 'out_refund') and -1 or 1
                price = sign * line.quant_id.cost * (1 - (line.discount or 0.0) / 100.0)

                taxes = line.invoice_line_tax_id.compute_all(price, 1, product=line.product_id,
                                                             partner=line.invoice_id.partner_id)
                dsoft_pret_aman = taxes['total_included']
                if line.invoice_id:
                    line.dsoft_pret_aman = dsoft_pret_aman

            else:
                line.dsoft_pret_aman = line.invoice_line_id.dsoft_pret_aman

    @api.multi
    def _compute_dsoft_pret_achiz1(self):
        for line in self:
            if line.invoice_id.type == 'in_invoice':
                line.dsoft_pret_achiz = line.invoice_line_id.dsoft_pret_achiz
            elif line.invoice_id.type in ('out_invoice', 'out_refund'):
                line.dsoft_pret_achiz = line.quant_id.cost

    @api.one
    def update_quants_dsoft_values(self):
        quants = []
        if self.product_id.type != 'service':
            if self.invoice_id.type == 'in_invoice':
                quants = self.invoice_line_id._get_quants(self)
            elif self.invoice_id.type in ('out_invoice', 'out_refund'):
                quants.append(self.quant_id)

            for qnt in quants:
                if qnt:
                    qnt.update_dsoft_values(self)


class account_invoice_tax(models.Model):
    _inherit = "account.invoice.tax"

    ##!!!!!!!!! COPY-PASTE-ADAPTED from base
    @api.v8
    def compute(self, invoice):
        tax_grouped = {}
        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))
        company_currency = invoice.company_id.currency_id
        for line in invoice.invoice_line:
            taxes = line.invoice_line_tax_id.compute_all(
                (line.price_unit * (1 - (line.discount or 0.0) / 100.0)),
                line.quantity, line.product_id, invoice.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(tax['price_unit'] * line['quantity']),
                }
                if invoice.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                ####### MY CODE ####################
                if line.name == 'TOTAL-F':
                    if  'TOTAL-F-TAX' in tax['name']:
                        val['amount'] = line.tax_subtotal
                    else:
                        val['amount'] = 0.0
                ##########################


                # If the taxes generate moves on the same financial account as the invoice line
                # and no default analytic account is defined at the tax level, propagate the
                # analytic account from the invoice line to the tax line. This is necessary
                # in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])
        return tax_grouped
