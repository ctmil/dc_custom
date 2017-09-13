# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.osv import osv
from openerp.exceptions import except_orm, ValidationError
from StringIO import StringIO
import urllib2, httplib, urlparse, gzip, requests, json
import openerp.addons.decimal_precision as dp
import logging
import datetime
from openerp.fields import Date as newdate
from datetime import datetime, timedelta, date
from dateutil import relativedelta
#Get the logger
_logger = logging.getLogger(__name__)

class account_analytic_line(models.Model):
        _inherit = 'account.analytic.line'

	@api.model
	def update_lines(self):
		lines = self.search([])
		for line in lines:
			vals = {}
			if not line.partner_id:
				if line.move_id and line.move_id.partner_id:
					vals['partner_id'] = line.move_id.partner_id.id
			if not line.journal_id:
				if line.move_id and line.move_id.journal_id:
					vals['journal_id'] = line.move_id.journal_id.id
			if vals:
				line.write(vals)

	journal_id = fields.Many2one('account.journal','Journal')
	

class purchase_order(models.Model):
        _inherit = 'purchase.order'

	@api.multi
	def _compute_cantidad(self):
		for po in self:
			cantidad = 0
			for line in po.order_line:
				cantidad = cantidad + line.product_qty
			po.cantidad = cantidad

	@api.multi
	def _compute_kilos_netos(self):
		for po in self:
			kilos_netos = 0
			for line in po.order_line:
				kilos_netos = kilos_netos + line.kilos_netos
			po.kilos_netos = kilos_netos

	@api.multi
	def _compute_kilos_brutos(self):
		for po in self:
			kilos_brutos = 0
			for line in po.order_line:
				kilos_brutos = kilos_brutos + line.kilos_brutos
			po.kilos_brutos = kilos_brutos
	
	@api.multi
	def _compute_desbaste(self):
		for po in self:
			if po.kilos_netos == 0:
				po.desbaste = 0
			else:
				po.desbaste = ((po.kilos_netos - po.kilos_llegada) / po.kilos_netos) * 100
			
	@api.multi
	def _compute_precio_kg(self):
		for po in self:
			if po.kilos_netos == 0:
				po.precio_kg = 0
			else:
				po.precio_kg = po.amount_total / po.kilos_netos

	@api.multi
	def _compute_precio_kg_desbaste(self):
		for po in self:
			if po.kilos_llegada == 0:
				po.precio_kg_desbaste = 0
			else:
				po.precio_kg_desbaste = po.amount_total / po.kilos_llegada

	@api.multi
	def _compute_precio_unidad(self):
		for po in self:
			if po.cantidad == 0:
				po.precio_unidad = 0
			else:
				po.precio_unidad = po.amount_total / po.cantidad

	origen = fields.Char('Origen')
	destino = fields.Char('Destino')
	cantidad = fields.Integer('Cantidad',compute=_compute_cantidad)
	kilos_netos = fields.Float('Kg Netos',compute=_compute_kilos_netos)
	kilos_brutos = fields.Float('Kg Brutos',compute=_compute_kilos_brutos)
	kilos_llegada = fields.Float('Kg Llegada')
	desbaste = fields.Float('Desbaste',compute=_compute_desbaste)
	precio_kg = fields.Float('Precio / Kg',compute=_compute_precio_kg)
	precio_kg_desbaste = fields.Float('Precio / Kg con Desbaste',compute=_compute_precio_kg_desbaste)
	precio_unidad = fields.Float('Precio Unidad',compute=_compute_precio_unidad)
	compra_hacienda_id = fields.Many2one('purchase.order',string='Compra de Hacienda')
	otras_compras_ids = fields.One2many(comodel_name='purchase.order.line',inverse_name='compra_hacienda_id',string='Compras relacionadas')

class account_invoice_line(models.Model):
	_inherit = 'account.invoice.line'

	@api.multi
	def _compute_kilos_unidad(self):
		for inl in self:
			if inl.quantity > 0:
				inl.kilos_unidad = inl.kilos / inl.quantity

	date_due = fields.Date('Fecha Vencimiento')
	kilos = fields.Float('Kilos')
	kilos_unidad = fields.Float('Kilos por unidad',compute=_compute_kilos_unidad)
	

class purchase_order_line(models.Model):
	_inherit = 'purchase.order.line'

	@api.multi
	def _compute_desbaste(self):
		for pol in self:
			if pol.kilos_netos > 0:
				pol.desbaste = ((pol.kilos_netos - pol.kilos_llegada) / pol.kilos_netos) *  100


	@api.multi
	def _compute_precio_kg(self):
		for pol in self:
			if pol.kilos_netos > 0:
				pol.precio_kg = pol.price_unit / pol.kilos_netos 

	@api.multi
	def _compute_precio_desbaste(self):
		for pol in self:
			if pol.kilos_llegada > 0:
				pol.precio_desbaste = pol.price_unit / pol.kilos_llegada

	kilos_brutos = fields.Float('Kilos Brutos')
	kilos_netos = fields.Float('Kilos Netos')
	kilos_llegada = fields.Float('Kilos Llegada')
	desbaste = fields.Float('Desbaste',compute=_compute_desbaste)
	precio_kg = fields.Float('Precio Kg',compute=_compute_precio_kg)
	precio_desbaste = fields.Float('Precio c/Desbaste',compute=_compute_precio_desbaste)
	compra_hacienda_id = fields.Many2one('purchase.order',string='Compra de Hacienda')
	date_order = fields.Datetime('Fecha Orden',related='order_id.date_order')
	partner_id = fields.Many2one('res.partner',related='order_id.partner_id')

class sale_order(models.Model):
        _inherit = 'sale.order'

	origen = fields.Char('Origen')
	destino = fields.Char('Destino')

class sale_order_line(models.Model):
	_inherit = 'sale.order.line'

	@api.multi
	def _compute_desbaste(self):
		for sol in self:
			if sol.kilos_netos > 0:
				sol.desbaste = ((sol.kilos_netos - sol.kilos_llegada) / sol.kilos_netos) *  100

	@api.multi
	def _compute_desbaste(self):
		for sol in self:
			if sol.kilos_netos > 0:
				sol.desbaste = ((sol.kilos_netos - sol.kilos_llegada) / sol.kilos_netos) *  100


	@api.multi
	def _compute_precio_kg(self):
		for sol in self:
			if sol.kilos_netos > 0:
				sol.precio_kg = sol.price_unit / sol.kilos_netos 

	@api.multi
	def _compute_precio_desbaste(self):
		for sol in self:
			if sol.kilos_llegada > 0:
				sol.precio_desbaste = sol.price_unit / sol.kilos_llegada

	kilos_brutos = fields.Float('Kilos Brutos')
	kilos_netos = fields.Float('Kilos Netos')
	kilos_llegada = fields.Float('Kilos Llegada')
	desbaste = fields.Float('Desbaste',compute=_compute_desbaste)
	precio_kg = fields.Float('Precio Kg',compute=_compute_precio_kg)
	precio_desbaste = fields.Float('Precio c/Desbaste',compute=_compute_precio_desbaste)
