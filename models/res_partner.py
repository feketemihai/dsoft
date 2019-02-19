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
from openerp import fields, models, api
from openerp.tools.misc import ustr

class res_partner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    @api.depends('vat')
    def compute_cod_fiscal(self):
        for p in self:
            p.dsoft_cod_fiscal = p.vat

    @api.multi
    @api.depends('name')
    def _compute_dsoft_denfur(self):
        for p in self:
            p.dsoft_denfur = p.name

    @api.onchange('vat')
    def compute_cod_fur(self):
        for p in self:
            p.dsoft_codfur = p.vat


    dsoft_denfur = fields.Char(string="DENFUR", size=30, compute="_compute_dsoft_denfur")
    dsoft_codfur = fields.Char(string="COD FURNIZOR")
    dsoft_cod_fiscal = fields.Char(string="COD_FISCAL", size=15, compute='compute_cod_fiscal')
    dsoft_tva_incas = fields.Selection([('DA', 'DA')], string="TVA_INCAS")

    @api.model
    def simple_vat_check(self, country_code, vat_number):
        return True
        # if not ustr(country_code).encode('utf-8').isalpha():
        # return super(res_partner, self).simple_vat_check(country_code, vat_number)
