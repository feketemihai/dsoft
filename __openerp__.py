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
{
    'name': 'DSOFT Connector',
    'version': '1.0',
    'category': 'App',
    'sequence': 2,
    'summary': '',
    'description': """
Integration wiht DSOFT accounting software
====================================================
""",
    'author': 'Temeron SRL',
    'website': 'http://www.temeron.ro',
    'depends': [
        'l10n_ro',
        'quant_analytic',
        'purchase',
        'purchase_discount',
        'base_vat',
        'procurement_jit',
        'procurement_jit_stock',
        'currency_rate_update'
    ],
    'qweb': [
    ],
    'data': [
        'data/dsoft_data.xml',
        'views/dsoft.xml',
        'data/dsoft_data_tax.xml',
        'data/dsoft_export.xml'
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
